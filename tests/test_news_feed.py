from __future__ import annotations

from dataclasses import replace

import pytest

from services.news_feed import NewsFeedService
from utils.errors import ConfigurationError, ExternalServiceError


class FakeResponse:
    def __init__(self, *, status_code: int, payload: dict, reason: str = "OK") -> None:
        self.status_code = status_code
        self.payload = payload
        self.reason = reason

    def json(self) -> dict:
        return self.payload


def test_news_feed_normalizes_gnews_articles(settings, monkeypatch) -> None:
    settings = replace(settings, news_api_key="news-key", news_cache_ttl_seconds=600)
    service = NewsFeedService(settings)
    calls = []

    def fake_get(url, *, params, timeout):
        calls.append({"url": url, "params": params, "timeout": timeout})
        return FakeResponse(
            status_code=200,
            payload={
                "articles": [
                    {
                        "title": "Bundestag debattiert neue Klimahilfen",
                        "description": "Die Koalition ringt um ein neues Paket.",
                        "url": "https://example.test/klima",
                        "image": "https://example.test/klima.jpg",
                        "publishedAt": "2026-04-15T08:00:00Z",
                        "source": {
                            "name": "Tagesschau",
                            "url": "https://tagesschau.de",
                        },
                    }
                ]
            },
        )

    monkeypatch.setattr("services.news_feed.requests.get", fake_get)

    result = service.get_headlines(category="Wirtschaft", limit=10)

    assert result["status"] == "ok"
    assert result["provider"] == "gnews"
    assert result["category"] == "Wirtschaft"
    assert result["headlines"][0]["headline"] == "Bundestag debattiert neue Klimahilfen"
    assert result["headlines"][0]["source"] == "Tagesschau"
    assert result["headlines"][0]["category"] == "Wirtschaft"
    assert calls[0]["params"]["category"] == "business"
    assert calls[0]["params"]["lang"] == "de"
    assert calls[0]["params"]["country"] == "de"

    cached = service.get_headlines(category="Wirtschaft", limit=10)
    assert cached["cached"] is True
    assert len(calls) == 1


def test_news_feed_requires_api_key(settings) -> None:
    service = NewsFeedService(settings)

    with pytest.raises(ConfigurationError, match="NEWS_API_KEY"):
        service.get_headlines(category="Schlagzeilen", limit=10)


def test_news_feed_surfaces_provider_errors(settings, monkeypatch) -> None:
    settings = replace(settings, news_api_key="news-key")
    service = NewsFeedService(settings)

    def fake_get(url, *, params, timeout):
        return FakeResponse(
            status_code=403,
            payload={"errors": ["Daily request limit reached"]},
            reason="Forbidden",
        )

    monkeypatch.setattr("services.news_feed.requests.get", fake_get)

    with pytest.raises(ExternalServiceError, match="Daily request limit reached"):
        service.get_headlines(category="Schlagzeilen", limit=10)
