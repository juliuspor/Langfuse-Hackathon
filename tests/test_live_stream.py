from __future__ import annotations

import json


def test_live_stream_emits_turns_and_completion(app_client) -> None:
    response = app_client.get(
        "/api/debate/live?topic=Energiepolitik&turns=3&language=de&include_audio=false",
        buffered=True,
    )

    assert response.status_code == 200
    assert response.mimetype == "text/event-stream"

    events = _parse_sse(response.get_data(as_text=True))
    assert [event["event"] for event in events] == [
        "connected",
        "conversation",
        "turn",
        "referee",
        "turn",
        "referee",
        "turn",
        "referee",
        "completed",
    ]
    assert events[1]["data"]["status"] == "running"
    assert events[2]["data"]["turn_index"] == 1
    assert events[3]["data"]["badge"] == "Gruen"
    assert events[-1]["data"]["status"] == "completed"
    assert len(events[-1]["data"]["turns"]) == 3


def test_live_stream_defaults_to_four_turns(app_client) -> None:
    response = app_client.get(
        "/api/debate/live?topic=Energiepolitik&language=de&include_audio=false",
        buffered=True,
    )

    assert response.status_code == 200
    events = _parse_sse(response.get_data(as_text=True))
    assert [event["event"] for event in events].count("turn") == 4
    assert [event["event"] for event in events].count("referee") == 4
    assert events[-1]["data"]["meta"]["total_turns"] == 4
    assert events[-1]["data"]["meta"]["fact_referee"]["judged_turns"] == 4
    assert len(events[-1]["data"]["turns"]) == 4


def test_live_stream_emits_text_turn_before_audio(app_client) -> None:
    response = app_client.get(
        "/api/debate/live?topic=Energiepolitik&turns=2&language=de&include_audio=true",
        buffered=True,
    )

    assert response.status_code == 200
    events = _parse_sse(response.get_data(as_text=True))
    assert [event["event"] for event in events] == [
        "connected",
        "conversation",
        "turn",
        "referee",
        "audio",
        "turn",
        "referee",
        "audio",
        "completed",
    ]
    assert events[2]["data"]["turn_index"] == 1
    assert events[2]["data"]["audio_url"] is None
    assert events[3]["data"]["turn_index"] == 1
    assert events[3]["data"]["verdict"] == "green"
    assert events[4]["data"]["turn_index"] == 1
    assert events[4]["data"]["audio_url"].endswith("/audio/1.mp3")
    assert events[-1]["data"]["turns"][0]["audio_url"].endswith("/audio/1.mp3")
    assert events[-1]["data"]["turns"][0]["referee"]["badge"] == "Gruen"


def test_live_stream_falls_back_when_generation_fails(
    app_client, storage, fake_elevenlabs_client
) -> None:
    fake_elevenlabs_client.fail_simulate_on_turn = 1

    response = app_client.get(
        "/api/debate/live?topic=Energiepolitik&turns=2&language=de&include_audio=false",
        buffered=True,
    )

    assert response.status_code == 200
    events = _parse_sse(response.get_data(as_text=True))
    assert [event["event"] for event in events] == [
        "connected",
        "conversation",
        "turn",
        "referee",
        "turn",
        "referee",
        "completed",
    ]
    conversation_id = events[1]["data"]["conversation_id"]
    stored = storage.get_conversation(conversation_id)
    assert stored is not None
    assert stored["status"] == "completed_with_warnings"
    assert len(stored["turns"]) == 2
    assert stored["meta"]["total_turns"] == 2
    assert "ElevenLabs conversation failed" in stored["meta"]["warnings"][0]
    assert fake_elevenlabs_client.simulate_calls == ["agent_1"]


def test_live_stream_continues_when_referee_fails(
    app_client, storage, fake_fact_referee_service
) -> None:
    fake_fact_referee_service.fail_on_turn = 2

    response = app_client.get(
        "/api/debate/live?topic=Energiepolitik&turns=3&language=de&include_audio=false",
        buffered=True,
    )

    assert response.status_code == 200
    events = _parse_sse(response.get_data(as_text=True))
    assert [event["event"] for event in events] == [
        "connected",
        "conversation",
        "turn",
        "referee",
        "turn",
        "turn",
        "completed",
    ]
    conversation_id = events[1]["data"]["conversation_id"]
    stored = storage.get_conversation(conversation_id)
    assert stored is not None
    assert stored["status"] == "completed_with_warnings"
    assert "Fakten-Schiri" in stored["meta"]["warnings"][-1]


def test_live_stream_rejects_invalid_boolean(app_client) -> None:
    response = app_client.get(
        "/api/debate/live?topic=Energiepolitik&turns=3&include_audio=maybe"
    )

    assert response.status_code == 422
    payload = response.get_json()
    assert "include_audio" in payload["error"]["message"]


def test_live_stream_rejects_non_german_language(app_client) -> None:
    response = app_client.get(
        "/api/debate/live?topic=Energiepolitik&turns=3&language=en"
    )

    assert response.status_code == 422
    payload = response.get_json()
    assert "language" in payload["error"]["message"]


def _parse_sse(raw: str) -> list[dict]:
    events = []
    for block in raw.strip().split("\n\n"):
        event_name = None
        data = None
        for line in block.splitlines():
            if line.startswith("event: "):
                event_name = line.removeprefix("event: ")
            if line.startswith("data: "):
                data = json.loads(line.removeprefix("data: "))
        events.append({"event": event_name, "data": data})
    return events
