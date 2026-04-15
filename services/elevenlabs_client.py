from __future__ import annotations

import time
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from utils.config import Settings
from utils.errors import ExternalServiceError


class ElevenLabsClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.base_url = settings.elevenlabs_base_url
        self._agent_voice_cache: dict[str, str | None] = {}
        self.session = requests.Session()
        retry = Retry(
            total=3,
            connect=3,
            read=0,
            status=3,
            backoff_factor=0.4,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=frozenset(["GET", "POST"]),
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry, pool_connections=10, pool_maxsize=10)
        self.session.mount("https://", adapter)
        self.default_headers = {
            "xi-api-key": settings.elevenlabs_api_key,
            "Content-Type": "application/json",
            "User-Agent": "lanz-precht-briefing-agent/0.1",
        }

    def simulate_turn(
        self,
        *,
        agent_id: str,
        partial_history: list[dict[str, Any]],
        language: str,
    ) -> dict[str, Any]:
        url = f"{self.base_url}/v1/convai/agents/{agent_id}/simulate-conversation"
        payload = {
            "simulation_specification": {
                "simulated_user_config": {
                    "language": language,
                    "prompt": {
                        "prompt": "Respond naturally to the provided user messages in one turn.",
                    },
                },
                "partial_conversation_history": partial_history,
            },
            "new_turns_limit": 1,
        }

        started = time.perf_counter()
        read_timeout = min(self.settings.request_timeout_seconds, 12.0)
        try:
            response = self.session.post(
                url,
                headers=self.default_headers,
                json=payload,
                timeout=(5, read_timeout),
            )
        except requests.Timeout as exc:
            raise ExternalServiceError(
                "ElevenLabs simulate-conversation timed out"
            ) from exc
        except requests.RequestException as exc:
            raise ExternalServiceError(
                "ElevenLabs simulate-conversation request failed"
            ) from exc

        latency_ms = (time.perf_counter() - started) * 1000
        if response.status_code >= 400:
            raise ExternalServiceError(
                self._build_error_message("simulate-conversation", response)
            )

        try:
            payload_response = response.json()
        except ValueError as exc:
            raise ExternalServiceError(
                "ElevenLabs simulate-conversation returned invalid JSON"
            ) from exc

        text = self._extract_latest_agent_text(
            payload_response.get("simulated_conversation", [])
        )
        if not text:
            raise ExternalServiceError(
                "ElevenLabs simulate-conversation returned no agent message"
            )

        return {
            "text": text,
            "latency_ms": latency_ms,
            "analysis": payload_response.get("analysis"),
            "raw": payload_response,
            "provider": self._extract_provider_metadata(response),
        }

    def get_agent_voice_id(self, *, agent_id: str) -> str | None:
        if agent_id in self._agent_voice_cache:
            return self._agent_voice_cache[agent_id]

        url = f"{self.base_url}/v1/convai/agents/{agent_id}"
        try:
            response = self.session.get(
                url,
                headers=self.default_headers,
                timeout=(5, self.settings.request_timeout_seconds),
            )
        except requests.Timeout as exc:
            raise ExternalServiceError("ElevenLabs get-agent timed out") from exc
        except requests.RequestException as exc:
            raise ExternalServiceError("ElevenLabs get-agent request failed") from exc

        if response.status_code >= 400:
            raise ExternalServiceError(self._build_error_message("get-agent", response))

        try:
            payload_response = response.json()
        except ValueError as exc:
            raise ExternalServiceError("ElevenLabs get-agent returned invalid JSON") from exc

        voice_id = (
            payload_response.get("conversation_config", {})
            .get("tts", {})
            .get("voice_id")
        )
        if not isinstance(voice_id, str) or not voice_id.strip():
            voice_id = None

        self._agent_voice_cache[agent_id] = voice_id
        return voice_id

    def synthesize_speech(
        self,
        *,
        voice_id: str,
        text: str,
        language: str,
    ) -> dict[str, Any]:
        url = f"{self.base_url}/v1/text-to-speech/{voice_id}"
        params: dict[str, Any] = {
            "output_format": self.settings.tts_output_format,
        }
        if self.settings.tts_optimize_streaming_latency is not None:
            params["optimize_streaming_latency"] = (
                self.settings.tts_optimize_streaming_latency
            )

        payload = {
            "text": text,
            "model_id": self.settings.tts_model_id,
            "language_code": language,
        }

        started = time.perf_counter()
        try:
            response = self.session.post(
                url,
                params=params,
                headers=self.default_headers,
                json=payload,
                timeout=(5, self.settings.request_timeout_seconds),
            )
        except requests.Timeout as exc:
            raise ExternalServiceError("ElevenLabs text-to-speech timed out") from exc
        except requests.RequestException as exc:
            raise ExternalServiceError(
                "ElevenLabs text-to-speech request failed"
            ) from exc

        latency_ms = (time.perf_counter() - started) * 1000
        if response.status_code >= 400:
            raise ExternalServiceError(
                self._build_error_message("text-to-speech", response)
            )

        if not response.content:
            raise ExternalServiceError("ElevenLabs text-to-speech returned empty audio")

        return {
            "audio_bytes": response.content,
            "latency_ms": latency_ms,
            "headers": dict(response.headers),
            "provider": self._extract_provider_metadata(response),
        }

    @staticmethod
    def _extract_latest_agent_text(
        simulated_conversation: list[dict[str, Any]],
    ) -> str | None:
        for turn in reversed(simulated_conversation):
            if turn.get("role") == "agent" and isinstance(turn.get("message"), str):
                message = turn["message"].strip()
                if message:
                    return message
        return None

    @staticmethod
    def _build_error_message(operation: str, response: requests.Response) -> str:
        detail: str | None = None
        try:
            payload = response.json()
            if isinstance(payload, dict):
                if isinstance(payload.get("detail"), str):
                    detail = payload["detail"]
                elif isinstance(payload.get("message"), str):
                    detail = payload["message"]
        except ValueError:
            detail = None
        if detail:
            return f"ElevenLabs {operation} failed ({response.status_code}): {detail}"
        return f"ElevenLabs {operation} failed with status {response.status_code}"

    @staticmethod
    def _extract_provider_metadata(response: requests.Response) -> dict[str, Any]:
        headers = response.headers
        provider_request_id = headers.get("request-id") or headers.get("x-request-id")
        character_count = ElevenLabsClient._parse_int_header(
            headers.get("x-character-count")
        )
        character_cost = ElevenLabsClient._parse_float_header(
            headers.get("x-character-cost")
        )
        return {
            "request_id": provider_request_id,
            "character_count": character_count,
            "character_cost": character_cost,
            "model_id": headers.get("x-model-id"),
        }

    @staticmethod
    def _parse_int_header(value: str | None) -> int | None:
        if value is None:
            return None
        try:
            return int(value)
        except ValueError:
            return None

    @staticmethod
    def _parse_float_header(value: str | None) -> float | None:
        if value is None:
            return None
        try:
            return float(value)
        except ValueError:
            return None
