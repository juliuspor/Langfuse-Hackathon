from __future__ import annotations


def test_start_requires_json_body(app_client) -> None:
    response = app_client.post(
        "/api/debate/start", data="not-json", content_type="text/plain"
    )
    assert response.status_code == 422
    payload = response.get_json()
    assert payload["error"]["code"] == "validation_error"


def test_start_rejects_invalid_turns(app_client) -> None:
    response = app_client.post(
        "/api/debate/start",
        json={
            "topic": "Klimapolitik",
            "turns": 1,
            "language": "de",
            "include_audio": False,
        },
    )
    assert response.status_code == 422
    payload = response.get_json()
    assert "turns" in payload["error"]["message"]


def test_start_rejects_invalid_include_audio(app_client) -> None:
    response = app_client.post(
        "/api/debate/start",
        json={
            "topic": "Klimapolitik",
            "turns": 4,
            "language": "de",
            "include_audio": "yes",
        },
    )
    assert response.status_code == 422
    payload = response.get_json()
    assert "include_audio" in payload["error"]["message"]
