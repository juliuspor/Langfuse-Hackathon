from __future__ import annotations

import json
import time
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import websocket
from websocket import WebSocketTimeoutException

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
        latest_user_message = self._extract_latest_user_message(partial_history)
        if not latest_user_message:
            raise ExternalServiceError(
                "ElevenLabs conversation websocket received no user message"
            )

        started = time.perf_counter()
        response_timeout_seconds = min(self.settings.request_timeout_seconds, 12.0)
        initiation_message = self._build_conversation_initiation_message(
            language=language
        )
        last_error: Exception | None = None

        for _attempt in range(1):
            try:
                signed_url = self._get_signed_conversation_url(agent_id=agent_id)
                text = self._chat_turn_via_websocket(
                    signed_url=signed_url,
                    initiation_message=initiation_message,
                    user_message=latest_user_message,
                    response_timeout_seconds=response_timeout_seconds,
                )
                latency_ms = (time.perf_counter() - started) * 1000

                return {
                    "text": text,
                    "latency_ms": latency_ms,
                    "analysis": None,
                    "raw": None,
                    "provider": {
                        "transport": "conversation_websocket",
                        "model_id": None,
                        "request_id": None,
                        "character_count": None,
                        "character_cost": None,
                    },
                }
            except TimeoutError as exc:
                last_error = exc
            except websocket.WebSocketException as exc:
                last_error = exc

        if isinstance(last_error, TimeoutError):
            raise ExternalServiceError(
                "ElevenLabs conversation websocket timed out"
            ) from last_error
        if isinstance(last_error, websocket.WebSocketException):
            raise ExternalServiceError(
                "ElevenLabs conversation websocket failed"
            ) from last_error
        raise ExternalServiceError("ElevenLabs conversation websocket failed")

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

    def _get_signed_conversation_url(self, *, agent_id: str) -> str:
        url = f"{self.base_url}/v1/convai/conversation/get-signed-url"
        try:
            response = self.session.get(
                url,
                headers=self.default_headers,
                params={"agent_id": agent_id},
                timeout=(5, self.settings.request_timeout_seconds),
            )
        except requests.Timeout as exc:
            raise ExternalServiceError(
                "ElevenLabs get-signed-url timed out"
            ) from exc
        except requests.RequestException as exc:
            raise ExternalServiceError(
                "ElevenLabs get-signed-url request failed"
            ) from exc

        if response.status_code >= 400:
            raise ExternalServiceError(
                self._build_error_message("get-signed-url", response)
            )

        try:
            payload = response.json()
        except ValueError as exc:
            raise ExternalServiceError(
                "ElevenLabs get-signed-url returned invalid JSON"
            ) from exc

        signed_url = payload.get("signed_url")
        if not isinstance(signed_url, str) or not signed_url.strip():
            raise ExternalServiceError(
                "ElevenLabs get-signed-url returned no signed URL"
            )
        return signed_url.strip()

    @staticmethod
    def _build_conversation_initiation_message(*, language: str) -> str:
        payload: dict[str, Any] = {
            "type": "conversation_initiation_client_data",
            "conversation_config_override": {
                "conversation": {
                    "text_only": True,
                }
            },
        }
        if language:
            payload["conversation_config_override"]["agent"] = {
                "language": language,
            }
        return json.dumps(payload, ensure_ascii=False)

    def _chat_turn_via_websocket(
        self,
        *,
        signed_url: str,
        initiation_message: str,
        user_message: str,
        response_timeout_seconds: float,
    ) -> str:
        ws = websocket.create_connection(signed_url, timeout=5)
        ws.settimeout(0.5)
        try:
            ws.send(initiation_message)
            self._wait_for_conversation_init(
                ws, timeout_seconds=min(response_timeout_seconds, 5.0)
            )
            ws.send(
                json.dumps(
                    {
                        "type": "user_message",
                        "text": user_message,
                    },
                    ensure_ascii=False,
                )
            )
            return self._wait_for_agent_response(
                ws, timeout_seconds=response_timeout_seconds
            )
        finally:
            ws.close()

    def _wait_for_conversation_init(
        self,
        ws: websocket.WebSocket,
        *,
        timeout_seconds: float,
    ) -> None:
        deadline = time.perf_counter() + timeout_seconds
        while time.perf_counter() < deadline:
            message = self._recv_json_message(ws)
            if message is None:
                continue
            self._respond_to_ping_if_needed(ws, message)
            if message.get("type") == "conversation_initiation_metadata":
                return
        raise TimeoutError("conversation initiation metadata timed out")

    def _wait_for_agent_response(
        self,
        ws: websocket.WebSocket,
        *,
        timeout_seconds: float,
    ) -> str:
        deadline = time.perf_counter() + timeout_seconds
        streamed_parts: list[str] = []
        while time.perf_counter() < deadline:
            message = self._recv_json_message(ws)
            if message is None:
                continue

            self._respond_to_ping_if_needed(ws, message)
            event_type = message.get("type")
            if event_type == "agent_response":
                agent_response = (
                    message.get("agent_response_event", {}).get("agent_response")
                )
                if isinstance(agent_response, str) and agent_response.strip():
                    return agent_response.strip()
            elif event_type == "agent_response_correction":
                corrected = (
                    message.get("agent_response_correction_event", {})
                    .get("corrected_agent_response")
                )
                if isinstance(corrected, str) and corrected.strip():
                    return corrected.strip()
            elif event_type == "agent_chat_response_part":
                part = message.get("text_response_part", {})
                if part.get("type") == "delta" and isinstance(part.get("text"), str):
                    streamed_parts.append(part["text"])
            elif event_type == "client_tool_call":
                raise ExternalServiceError(
                    "ElevenLabs conversation requested an unsupported client tool"
                )

        if streamed_parts:
            text = "".join(streamed_parts).strip()
            if text:
                return text
        raise TimeoutError("agent response timed out")

    @staticmethod
    def _recv_json_message(ws: websocket.WebSocket) -> dict[str, Any] | None:
        try:
            raw = ws.recv()
        except WebSocketTimeoutException:
            return None
        if not isinstance(raw, str) or not raw.strip():
            return None
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return None
        return parsed if isinstance(parsed, dict) else None

    @staticmethod
    def _respond_to_ping_if_needed(
        ws: websocket.WebSocket, message: dict[str, Any]
    ) -> None:
        if message.get("type") != "ping":
            return
        event_id = message.get("ping_event", {}).get("event_id")
        if event_id is None:
            return
        ws.send(json.dumps({"type": "pong", "event_id": event_id}))

    @staticmethod
    def _extract_latest_user_message(
        partial_history: list[dict[str, Any]],
    ) -> str | None:
        for turn in reversed(partial_history):
            if turn.get("role") != "user":
                continue
            message = turn.get("message")
            if isinstance(message, str) and message.strip():
                return message.strip()
        return None

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
