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
        "turn",
        "turn",
        "completed",
    ]
    assert events[1]["data"]["status"] == "running"
    assert events[2]["data"]["turn_index"] == 1
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
    assert events[-1]["data"]["meta"]["total_turns"] == 4
    assert len(events[-1]["data"]["turns"]) == 4


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
