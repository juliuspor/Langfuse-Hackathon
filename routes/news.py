from __future__ import annotations

from typing import Any

from flask import Blueprint, current_app, jsonify, request

from utils.errors import ValidationError

news_bp = Blueprint("news", __name__)


@news_bp.get("/api/news/headlines")
def get_headlines() -> Any:
    validated = _validate_headline_args(request.args)
    news_feed_service = current_app.extensions["news_feed_service"]
    result = news_feed_service.get_headlines(
        category=validated["category"],
        limit=validated["limit"],
    )
    return jsonify(result)


def _validate_headline_args(args: Any) -> dict[str, Any]:
    limit_raw = args.get("limit", "10")
    try:
        limit = int(limit_raw)
    except (TypeError, ValueError) as exc:
        raise ValidationError("Field 'limit' must be an integer") from exc

    if limit < 1 or limit > 10:
        raise ValidationError("Field 'limit' must be between 1 and 10")

    category = args.get("category", "Schlagzeilen")
    if not isinstance(category, str) or not category.strip():
        raise ValidationError("Field 'category' must be a non-empty string")

    return {"category": category.strip(), "limit": limit}
