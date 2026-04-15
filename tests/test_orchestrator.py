from __future__ import annotations


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


def test_mocked_tts_failure_returns_warning_status(
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


def test_prosody_tags_are_removed_before_output(orchestrator) -> None:
    cleaned = orchestrator._trim_to_sentence_limit(
        "Wir brauchen [fast] Fakten, keine [slow] Allgemeinplaetze. [pause 1s] Weiter."
    )

    assert cleaned == "Wir brauchen Fakten, keine Allgemeinplaetze. Weiter."
