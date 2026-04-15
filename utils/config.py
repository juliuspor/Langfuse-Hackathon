from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

from utils.errors import ConfigurationError


@dataclass(frozen=True)
class Settings:
    elevenlabs_api_key: str
    elevenlabs_agent_1_id: str
    elevenlabs_agent_2_id: str
    elevenlabs_voice_1_id: str | None
    elevenlabs_voice_2_id: str | None
    elevenlabs_base_url: str
    news_provider: str
    news_api_key: str | None
    news_country: str
    news_language: str
    news_cache_ttl_seconds: int
    database_path: Path
    audio_storage_dir: Path
    request_timeout_seconds: float
    tts_model_id: str
    tts_output_format: str
    tts_optimize_streaming_latency: int | None
    max_turns: int
    log_level: str


def _required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ConfigurationError(f"Missing required environment variable: {name}")
    return value


def _optional_env(name: str) -> str | None:
    value = os.getenv(name, "").strip()
    return value or None


def _int_env(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise ConfigurationError(
            f"Environment variable {name} must be an integer"
        ) from exc


def _float_env(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return float(raw)
    except ValueError as exc:
        raise ConfigurationError(
            f"Environment variable {name} must be a float"
        ) from exc


def load_settings() -> Settings:
    load_dotenv(override=False)

    timeout = _float_env("REQUEST_TIMEOUT_SECONDS", 45.0)
    if timeout <= 0:
        raise ConfigurationError("REQUEST_TIMEOUT_SECONDS must be greater than 0")

    max_turns = _int_env("MAX_TURNS", 20)
    if max_turns < 2:
        raise ConfigurationError("MAX_TURNS must be at least 2")

    news_cache_ttl_seconds = _int_env("NEWS_CACHE_TTL_SECONDS", 600)
    if news_cache_ttl_seconds < 0:
        raise ConfigurationError("NEWS_CACHE_TTL_SECONDS must be zero or greater")

    optimize_streaming_latency_raw = os.getenv("TTS_OPTIMIZE_STREAMING_LATENCY")
    optimize_streaming_latency: int | None
    if (
        optimize_streaming_latency_raw is None
        or optimize_streaming_latency_raw.strip() == ""
    ):
        optimize_streaming_latency = None
    else:
        try:
            optimize_streaming_latency = int(optimize_streaming_latency_raw)
        except ValueError as exc:
            raise ConfigurationError(
                "TTS_OPTIMIZE_STREAMING_LATENCY must be an integer between 0 and 4"
            ) from exc
        if optimize_streaming_latency < 0 or optimize_streaming_latency > 4:
            raise ConfigurationError(
                "TTS_OPTIMIZE_STREAMING_LATENCY must be between 0 and 4"
            )

    database_path = (
        Path(os.getenv("DATABASE_PATH", "data/debates.json")).expanduser().resolve()
    )
    audio_storage_dir = (
        Path(os.getenv("AUDIO_STORAGE_DIR", "data/audio")).expanduser().resolve()
    )

    return Settings(
        elevenlabs_api_key=_required_env("ELEVENLABS_API_KEY"),
        elevenlabs_agent_1_id=_required_env("ELEVENLABS_AGENT_1_ID"),
        elevenlabs_agent_2_id=_required_env("ELEVENLABS_AGENT_2_ID"),
        elevenlabs_voice_1_id=_optional_env("ELEVENLABS_VOICE_1_ID"),
        elevenlabs_voice_2_id=_optional_env("ELEVENLABS_VOICE_2_ID"),
        elevenlabs_base_url=os.getenv(
            "ELEVENLABS_BASE_URL", "https://api.elevenlabs.io"
        ).rstrip("/"),
        news_provider=os.getenv("NEWS_PROVIDER", "gnews").strip().lower(),
        news_api_key=_optional_env("NEWS_API_KEY"),
        news_country=os.getenv("NEWS_COUNTRY", "de").strip().lower() or "de",
        news_language=os.getenv("NEWS_LANGUAGE", "de").strip().lower() or "de",
        news_cache_ttl_seconds=news_cache_ttl_seconds,
        database_path=database_path,
        audio_storage_dir=audio_storage_dir,
        request_timeout_seconds=timeout,
        tts_model_id=os.getenv("TTS_MODEL_ID", "eleven_flash_v2_5"),
        tts_output_format=os.getenv("TTS_OUTPUT_FORMAT", "mp3_44100_128"),
        tts_optimize_streaming_latency=optimize_streaming_latency,
        max_turns=max_turns,
        log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
    )
