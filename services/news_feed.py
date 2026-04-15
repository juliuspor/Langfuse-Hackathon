from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import time
from typing import Any

import requests

from utils.config import Settings
from utils.errors import ConfigurationError, ExternalServiceError


CATEGORY_MAP = {
    "schlagzeilen": ("general", "Schlagzeilen"),
    "general": ("general", "Schlagzeilen"),
    "deutschland": ("nation", "Deutschland"),
    "nation": ("nation", "Deutschland"),
    "welt": ("world", "Welt"),
    "world": ("world", "Welt"),
    "wirtschaft": ("business", "Wirtschaft"),
    "business": ("business", "Wirtschaft"),
    "wissen": ("science", "Wissen"),
    "science": ("science", "Wissen"),
    "sport": ("sports", "Sport"),
    "sports": ("sports", "Sport"),
    "technologie": ("technology", "Technologie"),
    "technology": ("technology", "Technologie"),
    "gesundheit": ("health", "Gesundheit"),
    "health": ("health", "Gesundheit"),
}


@dataclass
class CacheEntry:
    expires_at: float
    payload: dict[str, Any]


class NewsFeedService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._cache: dict[tuple[str, int], CacheEntry] = {}

    def get_headlines(self, *, category: str, limit: int) -> dict[str, Any]:
        provider_category, display_category = self._normalize_category(category)
        cache_key = (provider_category, limit)
        cached = self._cache.get(cache_key)
        if cached and cached.expires_at > time.monotonic():
            return {**cached.payload, "cached": True}

        if self.settings.news_provider != "gnews":
            raise ConfigurationError(
                f"Unsupported NEWS_PROVIDER: {self.settings.news_provider}"
            )
        if not self.settings.news_api_key:
            raise ConfigurationError("Missing required environment variable: NEWS_API_KEY")

        payload = self._fetch_gnews_headlines(
            provider_category=provider_category,
            display_category=display_category,
            limit=limit,
        )
        self._cache[cache_key] = CacheEntry(
            expires_at=time.monotonic() + self.settings.news_cache_ttl_seconds,
            payload=payload,
        )
        return {**payload, "cached": False}

    def _fetch_gnews_headlines(
        self, *, provider_category: str, display_category: str, limit: int
    ) -> dict[str, Any]:
        try:
            response = requests.get(
                "https://gnews.io/api/v4/top-headlines",
                params={
                    "category": provider_category,
                    "lang": self.settings.news_language,
                    "country": self.settings.news_country,
                    "max": limit,
                    "apikey": self.settings.news_api_key,
                },
                timeout=self.settings.request_timeout_seconds,
            )
        except requests.RequestException as exc:
            raise ExternalServiceError("News provider request failed") from exc

        data = self._parse_response(response)
        articles = [
            self._normalize_gnews_article(article, display_category)
            for article in data.get("articles", [])
        ]
        articles = [article for article in articles if article["headline"]]

        return {
            "status": "ok",
            "provider": "gnews",
            "country": self.settings.news_country,
            "language": self.settings.news_language,
            "category": display_category,
            "limit": limit,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "headlines": articles[:limit],
        }

    @staticmethod
    def _parse_response(response: requests.Response) -> dict[str, Any]:
        try:
            data = response.json()
        except ValueError as exc:
            raise ExternalServiceError("News provider returned invalid JSON") from exc

        if response.status_code >= 400:
            message = data.get("errors") or data.get("message") or response.reason
            raise ExternalServiceError(f"News provider error: {message}")
        if not isinstance(data, dict):
            raise ExternalServiceError("News provider returned an unexpected response")
        return data

    @staticmethod
    def _normalize_category(category: str) -> tuple[str, str]:
        key = category.strip().lower()
        return CATEGORY_MAP.get(key, ("general", "Schlagzeilen"))

    @staticmethod
    def _normalize_gnews_article(
        article: dict[str, Any], display_category: str
    ) -> dict[str, Any]:
        headline = str(article.get("title") or "").strip()
        url = str(article.get("url") or "").strip()
        published_at = str(article.get("publishedAt") or "").strip()
        source = article.get("source") if isinstance(article.get("source"), dict) else {}
        source_name = str(source.get("name") or "Unbekannte Quelle").strip()

        unique_value = url or f"{headline}:{published_at}:{source_name}"
        article_id = hashlib.sha256(unique_value.encode("utf-8")).hexdigest()[:16]

        return {
            "id": article_id,
            "headline": headline,
            "teaser": str(article.get("description") or "").strip(),
            "source": source_name,
            "source_url": str(source.get("url") or "").strip() or None,
            "url": url or None,
            "image_url": str(article.get("image") or "").strip() or None,
            "published_at": published_at or None,
            "timeAgo": _format_time_ago(published_at),
            "category": display_category,
        }


def _format_time_ago(value: str) -> str:
    published_at = _parse_datetime(value)
    if published_at is None:
        return "gerade eben"

    seconds = max(0, int((datetime.now(timezone.utc) - published_at).total_seconds()))
    minutes = seconds // 60
    if minutes < 1:
        return "gerade eben"
    if minutes < 60:
        return f"vor {minutes} Min."

    hours = minutes // 60
    if hours < 24:
        return f"vor {hours} Std."

    days = hours // 24
    if days == 1:
        return "gestern"
    return f"vor {days} Tagen"


def _parse_datetime(value: str) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)
