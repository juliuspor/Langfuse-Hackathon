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


def test_audio_uses_agent_voice_when_env_voice_ids_are_missing(
    settings, storage, fake_elevenlabs_client
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
