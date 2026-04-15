from __future__ import annotations

from dataclasses import replace

from services.debate_orchestrator import DebateOrchestrator
from services.news_context import NewsContextService


def test_turn_alternation_logic(orchestrator, fake_elevenlabs_client, settings) -> None:
    result = orchestrator.start_debate(
        topic="Energiepolitik",
        turns=4,
        language="de",
        include_audio=False,
        request_id="req-alt",
    )

    assert fake_elevenlabs_client.simulate_calls == [
        settings.elevenlabs_agent_1_id,
        settings.elevenlabs_agent_2_id,
        settings.elevenlabs_agent_1_id,
        settings.elevenlabs_agent_2_id,
    ]
    assert [turn["speaker"] for turn in result["turns"]] == [
        "agent_1",
        "agent_2",
        "agent_1",
        "agent_2",
    ]


def test_generated_text_is_returned_without_post_processing(
    orchestrator, fake_elevenlabs_client
) -> None:
    fake_elevenlabs_client.turn_texts = [
        "Tem polimit [pause].",
        "Sauberer Precht-Text.",
    ]

    result = orchestrator.start_debate(
        topic="Tempolimit",
        turns=2,
        language="de",
        include_audio=False,
        request_id="req-raw",
    )

    assert result["turns"][0]["text"] == "Tem polimit [pause]."
    assert result["turns"][1]["text"] == "Sauberer Precht-Text."
    assert result["turns"][0]["referee"]["verdict"] == "green"
    assert result["turns"][1]["referee"]["verdict"] == "yellow"


def test_guidance_message_sets_distinct_speaker_roles(
    orchestrator, fake_elevenlabs_client
) -> None:
    fake_elevenlabs_client.turn_texts = [
        "Erster Punkt mit deutlich mehr als einem Satz, damit die Uebergabe an den zweiten Turn Substanz hat.",
        "Antwort vom zweiten Agenten.",
    ]

    orchestrator.start_debate(
        topic="Tempolimit",
        turns=2,
        language="de",
        include_audio=False,
        request_id="req-guidance",
    )

    first_guidance = fake_elevenlabs_client.simulate_requests[0]["partial_history"][-1][
        "message"
    ]
    second_guidance = fake_elevenlabs_client.simulate_requests[1]["partial_history"][-1][
        "message"
    ]

    assert "Du sprichst jetzt als Markus Lanz" in first_guidance
    assert "journalistisch, konkret und leicht skeptisch" in first_guidance
    assert "Erueffne die Debatte mit einer klaren ersten These" in first_guidance

    assert "Du sprichst jetzt als Richard David Precht" in second_guidance
    assert "philosophisch und zugespitzt" in second_guidance
    assert "zitiere den letzten Beitrag nicht woertlich aus" in second_guidance
    assert "Reagiere direkt auf den Kern des letzten Punkts von Markus Lanz" in (
        second_guidance
    )


def test_compress_latest_turn_uses_core_claim_without_full_quote() -> None:
    compressed = DebateOrchestrator._compress_latest_turn(
        "Erster Satz mit Kernthese. Zweiter Satz mit Ausschmueckung und viel "
        "mehr Text, der in der naechsten Anleitung nicht komplett landen soll."
    )

    assert compressed == "Erster Satz mit Kernthese."


def test_transcript_persistence(orchestrator, storage) -> None:
    result = orchestrator.start_debate(
        topic="Digitalisierung",
        turns=3,
        language="de",
        include_audio=False,
        request_id="req-db",
    )

    stored = storage.get_conversation(result["conversation_id"])
    assert stored is not None
    assert stored["status"] == "completed"
    assert stored["topic"] == "Digitalisierung"
    assert len(stored["turns"]) == 3
    assert stored["turns"][0]["raw_meta"]["referee"]["badge"] == "Gruen"


def test_article_context_is_used_for_news_context(orchestrator) -> None:
    result = orchestrator.start_debate(
        topic="Bundestag debattiert neue Klimahilfen",
        turns=2,
        language="de",
        include_audio=False,
        request_id="req-article",
        article_context={
            "source": "Tagesschau",
            "teaser": "Die Koalition ringt um ein neues Paket.",
            "url": "https://example.test/klima",
            "published_at": "2026-04-15T08:00:00Z",
        },
    )

    news_context = result["meta"]["news_context"]
    assert news_context["source"] == "news_article"
    assert news_context["article_source"] == "Tagesschau"
    assert "Die Koalition ringt" in news_context["context"]


def test_tts_failure_returns_warning_status(
    orchestrator, fake_elevenlabs_client
) -> None:
    fake_elevenlabs_client.fail_tts_on_turn = 2

    result = orchestrator.start_debate(
        topic="Bildungspolitik",
        turns=4,
        language="de",
        include_audio=True,
        request_id="req-tts",
    )

    assert result["status"] == "completed_with_warnings"
    assert result["turns"][0]["audio_url"] is not None
    assert result["turns"][1]["audio_url"] is None
    assert result["meta"]["warnings"]
    assert result["meta"]["fact_referee"]["judged_turns"] == 4


def test_audio_uses_agent_voice_when_env_voice_ids_are_missing(
    settings, storage, fake_elevenlabs_client, fake_fact_referee_service
) -> None:
    settings_without_voice_overrides = replace(
        settings,
        elevenlabs_voice_1_id=None,
        elevenlabs_voice_2_id=None,
    )
    fake_elevenlabs_client.agent_voice_ids = {
        settings.elevenlabs_agent_1_id: "agent_voice_1",
        settings.elevenlabs_agent_2_id: "agent_voice_2",
    }
    orchestrator = DebateOrchestrator(
        settings=settings_without_voice_overrides,
        storage=storage,
        elevenlabs_client=fake_elevenlabs_client,
        news_context_service=NewsContextService(),
        fact_referee_service=fake_fact_referee_service,
    )

    result = orchestrator.start_debate(
        topic="Bildungspolitik",
        turns=2,
        language="de",
        include_audio=True,
        request_id="req-agent-voice",
    )

    assert result["status"] == "completed"
    assert fake_elevenlabs_client.get_agent_voice_calls == [
        settings.elevenlabs_agent_1_id,
        settings.elevenlabs_agent_2_id,
    ]
    assert fake_elevenlabs_client.tts_calls == ["agent_voice_1", "agent_voice_2"]


def test_referee_failure_returns_warning_status(
    orchestrator, fake_fact_referee_service
) -> None:
    fake_fact_referee_service.fail_on_turn = 2

    result = orchestrator.start_debate(
        topic="Haushaltspolitik",
        turns=4,
        language="de",
        include_audio=False,
        request_id="req-ref-warning",
    )

    assert result["status"] == "completed_with_warnings"
    assert "Fakten-Schiri" in result["meta"]["warnings"][-1]
    assert result["turns"][0]["referee"]["verdict"] == "green"
    assert result["turns"][1]["referee"] is None
    assert result["turns"][2]["referee"] is None
