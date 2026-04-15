from __future__ import annotations

from dataclasses import dataclass
import uuid
from pathlib import Path
from typing import Any, Iterator

from models.storage import Storage
from services.elevenlabs_client import ElevenLabsClient
from services.fact_referee import FactRefereeService
from services.news_context import NewsContextService
from utils.config import Settings
from utils.errors import ExternalServiceError, NotFoundError


SPEAKER_ORDER = ("agent_1", "agent_2")


@dataclass(frozen=True)
class SpeakerProfile:
    agent_id: str
    voice_id: str | None


class DebateOrchestrator:
    """
    Agentic core: alternate personas, carry context, stream turns,
    and keep audio optional.
    """

    def __init__(
        self,
        *,
        settings: Settings,
        storage: Storage,
        elevenlabs_client: ElevenLabsClient,
        news_context_service: NewsContextService,
        fact_referee_service: FactRefereeService,
    ) -> None:
        self.settings = settings
        self.storage = storage
        self.elevenlabs_client = elevenlabs_client
        self.news_context_service = news_context_service
        self.fact_referee_service = fact_referee_service

    def start_debate(
        self,
        *,
        topic: str,
        turns: int,
        language: str,
        include_audio: bool,
        request_id: str,
        article_context: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        result: dict[str, Any] | None = None
        for event in self.iter_debate_events(
            topic=topic,
            turns=turns,
            language=language,
            include_audio=include_audio,
            request_id=request_id,
            article_context=article_context,
        ):
            if event["event"] == "completed":
                result = event["data"]
        if result is None:
            raise ExternalServiceError("Debate generation did not complete")
        return result

    def iter_debate_events(
        self,
        *,
        topic: str,
        turns: int,
        language: str,
        include_audio: bool,
        request_id: str,
        article_context: dict[str, str] | None = None,
    ) -> Iterator[dict[str, Any]]:
        conversation_id = str(uuid.uuid4())
        news_context = self.news_context_service.build_context(
            topic=topic, language=language, article_context=article_context
        )

        warnings: list[str] = []
        provider_character_count_total = 0
        provider_character_cost_total = 0.0
        referee_input_tokens_total = 0
        referee_output_tokens_total = 0
        referee_total_tokens_total = 0
        referee_failure_reason: str | None = None
        meta: dict[str, Any] = {
            "request_id": request_id,
            "news_context": news_context,
            "include_audio": include_audio,
            "warnings": warnings,
            "fact_referee": {
                "enabled": self.fact_referee_service.enabled,
                "model": self.settings.fact_referee_model,
                "judged_turns": 0,
            },
        }

        self.storage.create_conversation(
            conversation_id=conversation_id,
            topic=topic,
            language=language,
            status="running",
            meta=meta,
        )
        yield {
            "event": "conversation",
            "data": {
                "conversation_id": conversation_id,
                "topic": topic,
                "status": "running",
                "news_context": news_context,
                "fact_referee_enabled": self.fact_referee_service.enabled,
            },
        }

        transcript: list[dict[str, str]] = []
        text_fallback_reason: str | None = None
        try:
            for turn_index in range(1, turns + 1):
                speaker = self._speaker_for_turn(turn_index)
                profile = self._profile_for_speaker(speaker)
                guidance = self._build_guidance_message(
                    topic=topic,
                    news_context=news_context["context"],
                    transcript=transcript,
                    speaker=speaker,
                    language=language,
                    is_final_turn=turn_index == turns,
                )

                partial_history = self._build_partial_history(
                    transcript=transcript, speaker=speaker
                )
                partial_history.append(
                    {
                        "role": "user",
                        "message": guidance,
                        "time_in_call_secs": turn_index,
                    }
                )

                if text_fallback_reason is None:
                    try:
                        generation = self.elevenlabs_client.simulate_turn(
                            agent_id=profile.agent_id,
                            partial_history=partial_history,
                            language=language,
                        )
                    except ExternalServiceError as exc:
                        text_fallback_reason = str(exc)
                        warnings.append(
                            "ElevenLabs simulate-conversation failed; "
                            "used local fallback debate text."
                        )
                        generation = self._fallback_generation(
                            topic=topic,
                            news_context=news_context["context"],
                            transcript=transcript,
                            speaker=speaker,
                            turn_index=turn_index,
                            turns=turns,
                            reason=text_fallback_reason,
                        )
                else:
                    generation = self._fallback_generation(
                        topic=topic,
                        news_context=news_context["context"],
                        transcript=transcript,
                        speaker=speaker,
                        turn_index=turn_index,
                        turns=turns,
                        reason=text_fallback_reason,
                    )
                turn_text = generation["text"]

                audio_path: str | None = None
                turn_meta: dict[str, Any] = {
                    "generation_latency_ms": generation["latency_ms"],
                    "generation_provider": generation.get("provider"),
                }
                provider_character_count_total += int(
                    generation.get("provider", {}).get("character_count") or 0
                )
                provider_character_cost_total += float(
                    generation.get("provider", {}).get("character_cost") or 0
                )

                self.storage.add_turn(
                    conversation_id=conversation_id,
                    turn_index=turn_index,
                    speaker=speaker,
                    text=turn_text,
                    audio_path=audio_path,
                    latency_ms=generation["latency_ms"],
                    request_id=request_id,
                    raw_meta=turn_meta,
                )
                transcript.append({"speaker": speaker, "text": turn_text})
                yield {
                    "event": "turn",
                    "data": self._to_api_turn(
                        conversation_id=conversation_id,
                        turn={
                            "turn_index": turn_index,
                            "speaker": speaker,
                            "text": turn_text,
                            "audio_path": audio_path,
                            "raw_meta": turn_meta,
                        },
                    ),
                }

                if self.fact_referee_service.enabled and referee_failure_reason is None:
                    try:
                        referee = self.fact_referee_service.judge_turn(
                            topic=topic,
                            speaker=speaker,
                            turn_index=turn_index,
                            current_turn=turn_text,
                            previous_turn=transcript[-2]["text"]
                            if len(transcript) > 1
                            else None,
                            news_context=news_context,
                        )
                        turn_meta["referee"] = self._build_referee_verdict(
                            turn_index=turn_index,
                            speaker=speaker,
                            referee=referee,
                        )
                        turn_meta["referee_provider"] = referee.get("provider")
                        turn_meta["referee_latency_ms"] = referee["latency_ms"]
                        referee_provider = referee.get("provider", {})
                        referee_input_tokens_total += int(
                            referee_provider.get("input_tokens") or 0
                        )
                        referee_output_tokens_total += int(
                            referee_provider.get("output_tokens") or 0
                        )
                        referee_total_tokens_total += int(
                            referee_provider.get("total_tokens") or 0
                        )

                        self.storage.add_turn(
                            conversation_id=conversation_id,
                            turn_index=turn_index,
                            speaker=speaker,
                            text=turn_text,
                            audio_path=audio_path,
                            latency_ms=generation["latency_ms"],
                            request_id=request_id,
                            raw_meta=turn_meta,
                        )
                        yield {
                            "event": "referee",
                            "data": turn_meta["referee"],
                        }
                    except ExternalServiceError as exc:
                        referee_failure_reason = str(exc)
                        warnings.append(
                            "Fakten-Schiri ausgefallen; Debatte laeuft ohne weitere "
                            "Verifikationskarten weiter."
                        )

                if include_audio:
                    voice_id = profile.voice_id
                    if voice_id is None:
                        try:
                            voice_id = self.elevenlabs_client.get_agent_voice_id(
                                agent_id=profile.agent_id
                            )
                        except ExternalServiceError as exc:
                            warnings.append(
                                f"Could not load voice id for {speaker}: {str(exc)}"
                            )

                    if voice_id is None:
                        warnings.append(
                            f"Missing voice id for {speaker}; skipped audio for turn {turn_index}"
                        )
                    else:
                        try:
                            tts = self.elevenlabs_client.synthesize_speech(
                                voice_id=voice_id,
                                text=turn_text,
                                language=language,
                            )
                            audio_path = self._persist_audio(
                                conversation_id=conversation_id,
                                turn_index=turn_index,
                                audio_bytes=tts["audio_bytes"],
                            )
                            turn_meta["tts_latency_ms"] = tts["latency_ms"]
                            turn_meta["tts_provider"] = tts.get("provider")
                            provider_character_count_total += int(
                                tts.get("provider", {}).get("character_count") or 0
                            )
                            provider_character_cost_total += float(
                                tts.get("provider", {}).get("character_cost") or 0
                            )
                            self.storage.add_turn(
                                conversation_id=conversation_id,
                                turn_index=turn_index,
                                speaker=speaker,
                                text=turn_text,
                                audio_path=audio_path,
                                latency_ms=generation["latency_ms"],
                                request_id=request_id,
                                raw_meta=turn_meta,
                            )
                            yield {
                                "event": "audio",
                                "data": self._to_api_turn(
                                    conversation_id=conversation_id,
                                    turn={
                                        "turn_index": turn_index,
                                        "speaker": speaker,
                                        "text": turn_text,
                                        "audio_path": audio_path,
                                        "raw_meta": turn_meta,
                                    },
                                ),
                            }
                        except ExternalServiceError as exc:
                            warnings.append(
                                f"Audio generation failed for turn {turn_index}: {str(exc)}"
                            )
        except ExternalServiceError as exc:
            stored = self.storage.get_conversation(conversation_id)
            judged_turns = 0
            referee_summary = self._empty_referee_summary()
            if stored is not None:
                judged_turns = sum(
                    1
                    for turn in stored["turns"]
                    if (turn.get("raw_meta") or {}).get("referee")
                )
                referee_summary = self._count_referee_verdicts(stored["turns"])
            meta.update(
                {
                    "status": "failed",
                    "total_turns": len(transcript),
                    "error": str(exc),
                    "provider_usage": {
                        "character_count_total": provider_character_count_total,
                        "character_cost_total": round(provider_character_cost_total, 6),
                    },
                    "fact_referee": {
                        "enabled": self.fact_referee_service.enabled,
                        "model": self.settings.fact_referee_model,
                        "judged_turns": judged_turns,
                        "usage": {
                            "input_tokens_total": referee_input_tokens_total,
                            "output_tokens_total": referee_output_tokens_total,
                            "total_tokens_total": referee_total_tokens_total,
                        },
                        "summary": referee_summary,
                    },
                }
            )
            self.storage.update_conversation(
                conversation_id=conversation_id, status="failed", meta=meta
            )
            raise

        status = "completed_with_warnings" if warnings else "completed"
        stored = self.storage.get_conversation(conversation_id)
        judged_turns = 0
        referee_summary = self._empty_referee_summary()
        if stored is not None:
            judged_turns = sum(
                1
                for turn in stored["turns"]
                if (turn.get("raw_meta") or {}).get("referee")
            )
            referee_summary = self._count_referee_verdicts(stored["turns"])
        meta.update(
            {
                "status": status,
                "total_turns": turns,
                "provider_usage": {
                    "character_count_total": provider_character_count_total,
                    "character_cost_total": round(provider_character_cost_total, 6),
                },
                "fact_referee": {
                    "enabled": self.fact_referee_service.enabled,
                    "model": self.settings.fact_referee_model,
                    "judged_turns": judged_turns,
                    "usage": {
                        "input_tokens_total": referee_input_tokens_total,
                        "output_tokens_total": referee_output_tokens_total,
                        "total_tokens_total": referee_total_tokens_total,
                    },
                    "summary": referee_summary,
                },
            }
        )
        self.storage.update_conversation(
            conversation_id=conversation_id, status=status, meta=meta
        )
        yield {"event": "completed", "data": self.get_debate(conversation_id)}

    def get_debate(self, conversation_id: str) -> dict[str, Any]:
        stored = self.storage.get_conversation(conversation_id)
        if stored is None:
            raise NotFoundError(f"Conversation not found: {conversation_id}")
        return self._to_api_response(stored)

    def _profile_for_speaker(self, speaker: str) -> SpeakerProfile:
        profiles = {
            "agent_1": SpeakerProfile(
                agent_id=self.settings.elevenlabs_agent_1_id,
                voice_id=self.settings.elevenlabs_voice_1_id,
            ),
            "agent_2": SpeakerProfile(
                agent_id=self.settings.elevenlabs_agent_2_id,
                voice_id=self.settings.elevenlabs_voice_2_id,
            ),
        }
        return profiles[speaker]

    @staticmethod
    def _speaker_for_turn(turn_index: int) -> str:
        return SPEAKER_ORDER[(turn_index - 1) % len(SPEAKER_ORDER)]

    @staticmethod
    def _build_partial_history(
        transcript: list[dict[str, str]], speaker: str
    ) -> list[dict[str, Any]]:
        history: list[dict[str, Any]] = []
        for idx, turn in enumerate(transcript, start=1):
            history.append(
                {
                    "role": "agent" if turn["speaker"] == speaker else "user",
                    "message": turn["text"],
                    "time_in_call_secs": idx,
                }
            )
        return history

    @staticmethod
    def _build_guidance_message(
        *,
        topic: str,
        news_context: str,
        transcript: list[dict[str, str]],
        speaker: str,
        language: str,
        is_final_turn: bool,
    ) -> str:
        speaker_name = "Markus Lanz" if speaker == "agent_1" else "Richard David Precht"
        counterpart_name = (
            "Richard David Precht" if speaker == "agent_1" else "Markus Lanz"
        )
        persona_instruction = (
            "Sprich pointiert, journalistisch, konkret und leicht skeptisch. "
            "Kurze, druckvolle Saetze. Keine philosophische Vorlesung."
            if speaker == "agent_1"
            else "Sprich gedanklich, philosophisch und zugespitzt, aber bleibe "
            "konkret am Thema. Keine Moderationsfloskeln."
        )
        previous_claim = (
            DebateOrchestrator._compress_latest_turn(transcript[-1]["text"])
            if transcript
            else None
        )

        if language.lower().startswith("de"):
            opening = (
                f"Du sprichst jetzt als {speaker_name} im direkten Schlagabtausch mit {counterpart_name}. "
                f"{persona_instruction} "
                f"Thema: {topic}. Kontext: {news_context}. "
                "Antworte auf Deutsch in 2 bis 4 Saetzen. "
                "Bleibe in deiner Rolle, nenne deinen eigenen Namen nicht, "
                "wechsle nicht die Persona und zitiere den letzten Beitrag nicht woertlich aus."
            )
            if previous_claim:
                opening += (
                    f" Reagiere direkt auf den Kern des letzten Punkts von {counterpart_name}: "
                    f"{previous_claim}. Widersprich, praezisiere oder drehe den Gedanken weiter, "
                    "statt ihn nachzuerzaehlen."
                )
            else:
                opening += (
                    f" Erueffne die Debatte mit einer klaren ersten These zu {topic} "
                    "und setze sofort Spannung in die Sache."
                )
            if is_final_turn:
                opening += (
                    " Dies ist der letzte Turn. Benenne zum Schluss den tiefsten Dissens "
                    "und eine moegliche gemeinsame Basis."
                )
            return opening

        opening = (
            f"You are speaking as {speaker_name} in a direct exchange with {counterpart_name}. "
            f"{persona_instruction} "
            f"Topic: {topic}. Context: {news_context}. "
            "Reply in 2 to 4 sentences, stay in character, do not switch persona, and do not quote the previous turn verbatim."
        )
        if previous_claim:
            opening += (
                f" Respond directly to the core of {counterpart_name}'s latest point: "
                f"{previous_claim}. Push back or refine it instead of repeating it."
            )
        else:
            opening += f" Open the debate with a clear first claim about {topic}."
        if is_final_turn:
            opening += (
                " This is the final turn. Briefly name the deepest disagreement "
                "and any shared ground."
            )
        return opening

    @staticmethod
    def _compress_latest_turn(turn_text: str) -> str:
        cleaned = " ".join(turn_text.split()).strip().strip("'\"")
        if not cleaned:
            return ""

        sentence_end = min(
            (
                index
                for index, char in enumerate(cleaned)
                if char in ".!?"
            ),
            default=-1,
        )
        if 0 < sentence_end <= 180:
            cleaned = cleaned[: sentence_end + 1]
        elif len(cleaned) > 180:
            cleaned = cleaned[:177].rstrip() + "..."

        return cleaned

    @staticmethod
    def _fallback_generation(
        *,
        topic: str,
        news_context: str,
        transcript: list[dict[str, str]],
        speaker: str,
        turn_index: int,
        turns: int,
        reason: str,
    ) -> dict[str, Any]:
        return {
            "text": DebateOrchestrator._fallback_turn_text(
                topic=topic,
                news_context=news_context,
                transcript=transcript,
                speaker=speaker,
                turn_index=turn_index,
                turns=turns,
            ),
            "latency_ms": 0.0,
            "provider": {
                "name": "local_fallback",
                "error": reason,
            },
        }

    @staticmethod
    def _fallback_turn_text(
        *,
        topic: str,
        news_context: str,
        transcript: list[dict[str, str]],
        speaker: str,
        turn_index: int,
        turns: int,
    ) -> str:
        context_sentence = news_context.split(". ")[0].strip()
        if len(context_sentence) > 180:
            context_sentence = context_sentence[:177].rstrip() + "..."

        if turn_index == turns:
            if speaker == "agent_1":
                return (
                    f"Wenn man es herunterbricht, bleibt bei {topic} ein harter "
                    "Dissens: Was ist belegbar, und was ist nur Empoerung im "
                    "Morgennebel? Gemeinsam ist immerhin die Einsicht, dass man "
                    "bei duennen Fakten lieber nachfragt als sofort das grosse "
                    "Urteil faellt."
                )
            return (
                f"Der tiefere Punkt bei {topic} ist doch, dass oeffentliche "
                "Aufmerksamkeit schnell moralische Gewissheit simuliert. "
                "Gemeinsame Basis waere, erst die Quellen ernst zu nehmen und "
                "dann zu streiten, nicht umgekehrt."
            )

        if not transcript:
            if speaker == "agent_1":
                return (
                    f"Ich wuerde bei {topic} erst einmal die Bremse antippen: "
                    f"{context_sentence}. Daraus kann man eine Debatte machen, "
                    "aber bitte nicht so tun, als laege schon die ganze Wahrheit "
                    "auf dem Fruehstueckstisch."
                )
            return (
                f"Bei {topic} ist interessant, wie schnell aus einer Meldung ein "
                f"gesellschaftliches Symbol wird: {context_sentence}. Die Frage "
                "ist weniger, wer gerade recht hat, sondern warum uns diese "
                "Geschichte so zuverlaessig triggert."
            )

        previous = transcript[-1]["text"]
        if len(previous) > 150:
            previous = previous[:147].rstrip() + "..."

        if speaker == "agent_1":
            return (
                "Da hake ich ein: "
                f"'{previous}' klingt plausibel, aber mir fehlt der zweite "
                "Beleg. Gerade bei einer Schlagzeile muss man doch trennen "
                "zwischen Nachricht, Interpretation und dem kleinen Theater, "
                "das wir selbst daraus machen."
            )
        return (
            "Ja, aber diese Trennung ist selbst schon politisch: "
            f"'{previous}' zeigt, dass Fakten nie voellig nackt auftreten. "
            "Sie kommen mit Tonfall, Medium und Publikum, und genau dort beginnt "
            "die eigentliche Debatte."
        )

    def _persist_audio(
        self, *, conversation_id: str, turn_index: int, audio_bytes: bytes
    ) -> str:
        directory = Path(self.settings.audio_storage_dir) / conversation_id
        directory.mkdir(parents=True, exist_ok=True)
        output_path = directory / f"{turn_index}.mp3"
        output_path.write_bytes(audio_bytes)
        return str(output_path)

    def _to_api_response(self, stored: dict[str, Any]) -> dict[str, Any]:
        turns: list[dict[str, Any]] = []
        for turn in stored["turns"]:
            turns.append(
                self._to_api_turn(
                    conversation_id=stored["conversation_id"],
                    turn=turn,
                )
            )

        return {
            "conversation_id": stored["conversation_id"],
            "topic": stored["topic"],
            "status": stored["status"],
            "turns": turns,
            "meta": stored["meta"],
        }

    @staticmethod
    def _to_api_turn(conversation_id: str, turn: dict[str, Any]) -> dict[str, Any]:
        audio_url: str | None = None
        if turn["audio_path"]:
            audio_url = (
                f"/api/debate/{conversation_id}/audio/{turn['turn_index']}.mp3"
            )
        referee = None
        raw_meta = turn.get("raw_meta") or {}
        if isinstance(raw_meta, dict):
            referee = raw_meta.get("referee")
        return {
            "turn_index": turn["turn_index"],
            "speaker": turn["speaker"],
            "text": turn["text"],
            "audio_url": audio_url,
            "referee": referee,
        }

    @staticmethod
    def _build_referee_verdict(
        *, turn_index: int, speaker: str, referee: dict[str, Any]
    ) -> dict[str, Any]:
        return {
            "turn_index": turn_index,
            "speaker": speaker,
            "verdict": referee["verdict"],
            "badge": referee["badge"],
            "reason": referee["reason"],
            "confidence": referee["confidence"],
        }

    @staticmethod
    def _empty_referee_summary() -> dict[str, dict[str, int]]:
        summary: dict[str, dict[str, int]] = {}
        for speaker in SPEAKER_ORDER:
            summary[speaker] = {
                "green": 0,
                "yellow": 0,
                "red": 0,
                "offside": 0,
            }
        return summary

    @classmethod
    def _count_referee_verdicts(
        cls, turns: list[dict[str, Any]]
    ) -> dict[str, dict[str, int]]:
        summary = cls._empty_referee_summary()
        for turn in turns:
            raw_meta = turn.get("raw_meta") or {}
            if not isinstance(raw_meta, dict):
                continue
            referee = raw_meta.get("referee") or {}
            if not isinstance(referee, dict):
                continue
            speaker = turn.get("speaker")
            verdict = referee.get("verdict")
            if speaker in summary and verdict in summary[speaker]:
                summary[speaker][verdict] += 1
        return summary
