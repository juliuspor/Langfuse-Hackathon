from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from flask import Blueprint, Response, current_app, g, jsonify, request, send_file
from flask import stream_with_context

from utils.errors import AppError, NotFoundError, ValidationError

debate_bp = Blueprint("debate", __name__)
DEFAULT_TURNS = 4


@debate_bp.post("/api/debate/start")
def start_debate() -> Any:
    payload = request.get_json(silent=True)
    if payload is None:
        raise ValidationError("Request body must be valid JSON")

    settings = current_app.extensions["settings"]
    validated = _validate_start_payload(payload, max_turns=settings.max_turns)
    orchestrator = current_app.extensions["debate_orchestrator"]

    result = orchestrator.start_debate(
        topic=validated["topic"],
        turns=validated["turns"],
        language=validated["language"],
        include_audio=validated["include_audio"],
        article_context=validated["article_context"],
        request_id=g.request_id,
    )
    return jsonify(result)


@debate_bp.get("/api/debate/live")
def live_debate() -> Any:
    # SSE keeps the hackathon demo visibly alive: each agent turn reaches the UI
    # as soon as it is ready instead of hiding the debate behind one long wait.
    settings = current_app.extensions["settings"]
    validated = _validate_live_args(request.args, max_turns=settings.max_turns)
    orchestrator = current_app.extensions["debate_orchestrator"]
    request_id = g.request_id

    def generate():
        try:
            yield _sse(
                "connected",
                {
                    "status": "connected",
                    "request_id": request_id,
                },
            )
            for event in orchestrator.iter_debate_events(
                topic=validated["topic"],
                turns=validated["turns"],
                language=validated["language"],
                include_audio=validated["include_audio"],
                article_context=validated["article_context"],
                request_id=request_id,
            ):
                yield _sse(event["event"], event["data"])
        except AppError as exc:
            yield _sse(
                "error",
                {
                    "code": exc.code,
                    "message": exc.message,
                    "request_id": request_id,
                },
            )
        except Exception:
            current_app.logger.exception(
                "request_id=%s live_debate_stream_failed", request_id
            )
            yield _sse(
                "error",
                {
                    "code": "internal_error",
                    "message": "Unexpected internal server error",
                    "request_id": request_id,
                },
            )

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@debate_bp.get("/api/debate/<conversation_id>")
def get_debate(conversation_id: str) -> Any:
    orchestrator = current_app.extensions["debate_orchestrator"]
    result = orchestrator.get_debate(conversation_id)
    return jsonify(result)


@debate_bp.get("/api/debate/<conversation_id>/audio/<int:turn_index>.mp3")
def get_turn_audio(conversation_id: str, turn_index: int) -> Any:
    storage = current_app.extensions["storage"]
    settings = current_app.extensions["settings"]

    audio_path = storage.get_turn_audio_path(
        conversation_id=conversation_id, turn_index=turn_index
    )
    if not audio_path:
        raise NotFoundError("Audio for this turn was not found")

    resolved = Path(audio_path).resolve()
    audio_root = Path(settings.audio_storage_dir).resolve()
    if audio_root not in resolved.parents:
        raise NotFoundError("Audio file path is invalid")
    if not resolved.exists() or not resolved.is_file():
        raise NotFoundError("Audio file is missing")

    return send_file(
        resolved,
        mimetype="audio/mpeg",
        as_attachment=False,
        download_name=f"{turn_index}.mp3",
    )


def _validate_start_payload(
    payload: dict[str, Any], *, max_turns: int
) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValidationError("Request body must be a JSON object")

    topic = payload.get("topic")
    if not isinstance(topic, str) or not topic.strip():
        raise ValidationError(
            "Field 'topic' is required and must be a non-empty string"
        )

    turns = payload.get("turns", DEFAULT_TURNS)
    if isinstance(turns, bool) or not isinstance(turns, int):
        raise ValidationError("Field 'turns' must be an integer")
    if turns < 2 or turns > max_turns:
        raise ValidationError(f"Field 'turns' must be between 2 and {max_turns}")

    language = payload.get("language", "de")
    if not isinstance(language, str) or not language.strip():
        raise ValidationError("Field 'language' must be a non-empty string")
    if language.strip().lower() != "de":
        raise ValidationError("Field 'language' only supports 'de'")

    include_audio = payload.get("include_audio", True)
    if not isinstance(include_audio, bool):
        raise ValidationError("Field 'include_audio' must be a boolean")

    return {
        "topic": topic.strip(),
        "turns": turns,
        "language": language.strip(),
        "include_audio": include_audio,
        "article_context": _validate_article_context(payload),
    }


def _validate_live_args(args: Any, *, max_turns: int) -> dict[str, Any]:
    turns_raw = args.get("turns", str(DEFAULT_TURNS))
    try:
        turns = int(turns_raw)
    except (TypeError, ValueError) as exc:
        raise ValidationError("Field 'turns' must be an integer") from exc

    include_audio_raw = str(args.get("include_audio", "true")).strip().lower()
    if include_audio_raw in {"1", "true", "yes", "on"}:
        include_audio = True
    elif include_audio_raw in {"0", "false", "no", "off"}:
        include_audio = False
    else:
        raise ValidationError("Field 'include_audio' must be a boolean")

    return _validate_start_payload(
        {
            "topic": args.get("topic", ""),
            "turns": turns,
            "language": args.get("language", "de"),
            "include_audio": include_audio,
            "article_url": args.get("article_url"),
            "article_source": args.get("article_source"),
            "article_teaser": args.get("article_teaser"),
            "article_published_at": args.get("article_published_at"),
        },
        max_turns=max_turns,
    )


def _sse(event: str, data: dict[str, Any]) -> str:
    return (
        f"event: {event}\n"
        f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
    )


def _validate_article_context(payload: dict[str, Any]) -> dict[str, str] | None:
    fields = {
        "url": payload.get("article_url"),
        "source": payload.get("article_source"),
        "teaser": payload.get("article_teaser"),
        "published_at": payload.get("article_published_at"),
    }
    context: dict[str, str] = {}
    for key, value in fields.items():
        if value is None or value == "":
            continue
        if not isinstance(value, str):
            raise ValidationError(f"Field 'article_{key}' must be a string")
        context[key] = value.strip()[:800]
    return context or None
