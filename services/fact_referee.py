from __future__ import annotations

import json
import time
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from utils.config import Settings
from utils.errors import ExternalServiceError

OPENAI_RESPONSES_URL = "https://api.openai.com/v1/responses"

VERDICT_LABELS = {
    "green": "Gruen",
    "yellow": "Gelb",
    "red": "Rot",
    "offside": "Abseits",
}

_VERDICT_SCHEMA: dict[str, Any] = {
    "name": "fact_referee_verdict",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "verdict": {
                "type": "string",
                "enum": ["green", "yellow", "red", "offside"],
            },
            "reason": {
                "type": "string",
                "description": (
                    "A short German explanation for viewers in at most two sentences."
                ),
            },
            "confidence": {
                "type": "integer",
                "minimum": 0,
                "maximum": 100,
            },
        },
        "required": ["verdict", "reason", "confidence"],
        "additionalProperties": False,
    },
}


class FactRefereeService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.enabled = settings.fact_referee_enabled and bool(settings.openai_api_key)
        self.session: requests.Session | None = None
        if not self.enabled:
            return

        retry = Retry(
            total=2,
            connect=2,
            read=0,
            status=2,
            backoff_factor=0.4,
            status_forcelist=(408, 429, 500, 502, 503, 504),
            allowed_methods=frozenset(["POST"]),
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry, pool_connections=10, pool_maxsize=10)
        session = requests.Session()
        session.mount("https://", adapter)
        self.session = session

    def judge_turn(
        self,
        *,
        topic: str,
        speaker: str,
        turn_index: int,
        current_turn: str,
        previous_turn: str | None,
        news_context: dict[str, str],
    ) -> dict[str, Any]:
        if not self.enabled or self.session is None or not self.settings.openai_api_key:
            raise ExternalServiceError("Fact referee is not configured")

        system_prompt = (
            "Du bist der Fakten-Schiri fuer eine deutsche Live-News-Debatte. "
            "Bewerte nur anhand des gelieferten Quellenkontexts und des direkten "
            "Gesprächsverlaufs. Erfinde keine neuen Fakten. "
            "Nutze green nur, wenn die Aussage vom Kontext getragen ist oder "
            "vorsichtig sauber formuliert wurde. "
            "Nutze yellow bei Zuspitzung, fehlender Nuance oder leicht ueberdehnten "
            "Schluessen. Nutze red bei klar nicht gestuetzten Behauptungen. "
            "Nutze offside, wenn die Antwort dem letzten Punkt ausweicht oder das "
            "Thema deutlich verfehlt. "
            "Die reason muss kurz, oeffentlich vorzeigbar und auf Deutsch sein."
        )
        previous_turn_text = previous_turn or "Kein vorheriger Turn."
        source = news_context.get("article_source") or news_context.get("source") or "topic"
        user_prompt = (
            f"Thema: {topic}\n"
            f"Sprecher: {speaker}\n"
            f"Turn: {turn_index}\n"
            f"Quelle: {source}\n"
            f"Quellenkontext:\n{news_context.get('context', '')}\n\n"
            f"Vorheriger Turn:\n{previous_turn_text}\n\n"
            f"Aktueller Turn:\n{current_turn}\n\n"
            "Gib genau ein JSON-Objekt gemaess Schema zurueck."
        )

        payload = {
            "model": self.settings.fact_referee_model,
            "input": [
                {
                    "role": "system",
                    "content": [{"type": "input_text", "text": system_prompt}],
                },
                {
                    "role": "user",
                    "content": [{"type": "input_text", "text": user_prompt}],
                },
            ],
            "text": {
                "format": {
                    "type": "json_schema",
                    **_VERDICT_SCHEMA,
                }
            },
        }

        started = time.perf_counter()
        try:
            response = self.session.post(
                OPENAI_RESPONSES_URL,
                headers={
                    "Authorization": f"Bearer {self.settings.openai_api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=(5, self.settings.request_timeout_seconds),
            )
        except requests.Timeout as exc:
            raise ExternalServiceError("OpenAI fact referee timed out") from exc
        except requests.RequestException as exc:
            raise ExternalServiceError("OpenAI fact referee request failed") from exc

        latency_ms = (time.perf_counter() - started) * 1000
        if response.status_code >= 400:
            raise ExternalServiceError(self._build_error_message(response))

        try:
            payload_response = response.json()
        except ValueError as exc:
            raise ExternalServiceError("OpenAI fact referee returned invalid JSON") from exc

        raw_text = self._extract_output_text(payload_response)
        if raw_text is None:
            raise ExternalServiceError("OpenAI fact referee returned no verdict payload")

        try:
            parsed = json.loads(raw_text)
        except json.JSONDecodeError as exc:
            raise ExternalServiceError(
                "OpenAI fact referee returned malformed verdict JSON"
            ) from exc

        verdict = parsed.get("verdict")
        if verdict not in VERDICT_LABELS:
            raise ExternalServiceError("OpenAI fact referee returned an unknown verdict")

        reason = str(parsed.get("reason", "")).strip()
        if not reason:
            raise ExternalServiceError("OpenAI fact referee returned no reason")

        confidence = parsed.get("confidence")
        if not isinstance(confidence, int):
            raise ExternalServiceError(
                "OpenAI fact referee returned an invalid confidence value"
            )

        return {
            "verdict": verdict,
            "badge": VERDICT_LABELS[verdict],
            "reason": reason[:240],
            "confidence": max(0, min(100, confidence)),
            "latency_ms": latency_ms,
            "provider": self._extract_provider_metadata(
                response=response,
                payload_response=payload_response,
            ),
        }

    @staticmethod
    def _build_error_message(response: requests.Response) -> str:
        detail: str | None = None
        try:
            payload = response.json()
        except ValueError:
            payload = None

        if isinstance(payload, dict):
            error = payload.get("error")
            if isinstance(error, dict):
                message = error.get("message")
                if isinstance(message, str) and message.strip():
                    detail = message.strip()

        if detail:
            return f"OpenAI fact referee failed ({response.status_code}): {detail}"
        return f"OpenAI fact referee failed with status {response.status_code}"

    @staticmethod
    def _extract_output_text(payload_response: dict[str, Any]) -> str | None:
        output_text = payload_response.get("output_text")
        if isinstance(output_text, str) and output_text.strip():
            return output_text.strip()

        for item in payload_response.get("output", []):
            if not isinstance(item, dict):
                continue
            for content in item.get("content", []):
                if not isinstance(content, dict):
                    continue
                text = content.get("text")
                if content.get("type") in {"output_text", "text"} and isinstance(
                    text, str
                ):
                    cleaned = text.strip()
                    if cleaned:
                        return cleaned
        return None

    @staticmethod
    def _extract_provider_metadata(
        *, response: requests.Response, payload_response: dict[str, Any]
    ) -> dict[str, Any]:
        usage = payload_response.get("usage", {})
        return {
            "request_id": response.headers.get("x-request-id")
            or response.headers.get("request-id"),
            "model": payload_response.get("model"),
            "input_tokens": FactRefereeService._coerce_int(
                usage.get("input_tokens")
            ),
            "output_tokens": FactRefereeService._coerce_int(
                usage.get("output_tokens")
            ),
            "total_tokens": FactRefereeService._coerce_int(
                usage.get("total_tokens")
            ),
        }

    @staticmethod
    def _coerce_int(value: Any) -> int | None:
        if isinstance(value, bool):
            return None
        if isinstance(value, int):
            return value
        if isinstance(value, float):
            return int(value)
        return None
