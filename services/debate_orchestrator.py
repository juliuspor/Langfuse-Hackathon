from __future__ import annotations

from dataclasses import dataclass
import uuid
from pathlib import Path
from typing import Any, Iterator

from models.storage import Storage
from services.elevenlabs_client import ElevenLabsClient
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
    ) -> None:
        self.settings = settings
        self.storage = storage
        self.elevenlabs_client = elevenlabs_client
        self.news_context_service = news_context_service

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
        meta: dict[str, Any] = {
            "request_id": request_id,
            "news_context": news_context,
            "include_audio": include_audio,
            "warnings": warnings,
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
            },
        }

        transcript: list[dict[str, str]] = []
        for turn_index in range(1, turns + 1):
            speaker = self._speaker_for_turn(turn_index)
            profile = self._profile_for_speaker(speaker)
            guidance = self._build_guidance_message(
                topic=topic,
                news_context=news_context["context"],
                transcript=transcript,
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

            generation = self.elevenlabs_client.simulate_turn(
                agent_id=profile.agent_id,
                partial_history=partial_history,
                language=language,
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
                    except ExternalServiceError as exc:
                        warnings.append(
                            f"Audio generation failed for turn {turn_index}: {str(exc)}"
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
                    },
                ),
            }

        status = "completed_with_warnings" if warnings else "completed"
        meta.update(
            {
                "status": status,
                "total_turns": turns,
                "provider_usage": {
                    "character_count_total": provider_character_count_total,
                    "character_cost_total": round(provider_character_cost_total, 6),
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
        language: str,
        is_final_turn: bool,
    ) -> str:
        if language.lower().startswith("de"):
            opening = (
                f"Thema: {topic}. Kontext: {news_context}. "
                "Fuehre eine klare Debattenantwort in 2 bis 5 Saetzen aus, bleibe beim Thema und formuliere Unsicherheit vorsichtig."
            )
            if transcript:
                opening += f" Gehe direkt auf diese letzte Aussage ein: {transcript[-1]['text']}"
            if is_final_turn:
                opening += " Dies ist der letzte Turn. Nenne kurz den tiefsten Dissens und moegliche gemeinsame Basis."
            return opening

        opening = (
            f"Topic: {topic}. Context: {news_context}. "
            "Give one clear debate response in 2 to 5 sentences, stay on topic, and phrase uncertainty carefully."
        )
        if transcript:
            opening += (
                f" Respond directly to this latest point: {transcript[-1]['text']}"
            )
        if is_final_turn:
            opening += " This is the final turn. Briefly name the deepest disagreement and any shared ground."
        return opening

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
        return {
            "turn_index": turn["turn_index"],
            "speaker": turn["speaker"],
            "text": turn["text"],
            "audio_url": audio_url,
        }
