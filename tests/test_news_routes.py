from __future__ import annotations


class FakeNewsFeedService:
    def __init__(self) -> None:
        self.calls = []

    def get_headlines(self, *, category: str, limit: int) -> dict:
        self.calls.append({"category": category, "limit": limit})
        return {
            "status": "ok",
            "provider": "fake",
            "category": category,
            "headlines": [
                {
                    "id": "story-1",
                    "headline": "Aktuelle Meldung",
                    "teaser": "Kurzfassung",
                    "source": "Testquelle",
                    "timeAgo": "gerade eben",
                    "category": category,
                }
            ],
        }


def test_headlines_endpoint_returns_normalized_feed(app_client) -> None:
    fake_service = FakeNewsFeedService()
    app_client.application.extensions["news_feed_service"] = fake_service

    response = app_client.get("/api/news/headlines?limit=5&category=Welt")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["status"] == "ok"
    assert payload["headlines"][0]["headline"] == "Aktuelle Meldung"
    assert fake_service.calls == [{"category": "Welt", "limit": 5}]


def test_headlines_endpoint_rejects_invalid_limit(app_client) -> None:
    response = app_client.get("/api/news/headlines?limit=25")

    assert response.status_code == 422
    payload = response.get_json()
    assert "limit" in payload["error"]["message"]
