from __future__ import annotations

import logging
from pathlib import Path
import time
import uuid
from typing import Any

from flask import Flask, g, jsonify, request, send_from_directory
from werkzeug.exceptions import HTTPException

from models.storage import Storage
from routes.debate import debate_bp
from routes.news import news_bp
from services.debate_orchestrator import DebateOrchestrator
from services.elevenlabs_client import ElevenLabsClient
from services.fact_referee import FactRefereeService
from services.news_context import NewsContextService
from services.news_feed import NewsFeedService
from utils.config import Settings, load_settings
from utils.errors import AppError, ConfigurationError

FRONTEND_BUILD_DIR = Path(__file__).resolve().parent / "static" / "frontend"


def create_app(test_config: dict[str, Any] | None = None) -> Flask:
    test_config = test_config or {}
    settings = test_config.get("SETTINGS") or load_settings()

    _configure_logging(settings.log_level)

    app = Flask(__name__)
    app.config.update(test_config)

    storage: Storage = test_config.get("STORAGE") or Storage(settings.database_path)
    storage.init_db()

    elevenlabs_client = test_config.get("ELEVENLABS_CLIENT") or ElevenLabsClient(
        settings
    )
    news_context_service = (
        test_config.get("NEWS_CONTEXT_SERVICE") or NewsContextService()
    )
    fact_referee_service = (
        test_config.get("FACT_REFEREE_SERVICE") or FactRefereeService(settings)
    )
    news_feed_service = test_config.get("NEWS_FEED_SERVICE") or NewsFeedService(
        settings
    )
    debate_orchestrator = test_config.get("DEBATE_ORCHESTRATOR") or DebateOrchestrator(
        settings=settings,
        storage=storage,
        elevenlabs_client=elevenlabs_client,
        news_context_service=news_context_service,
        fact_referee_service=fact_referee_service,
    )

    app.extensions["settings"] = settings
    app.extensions["storage"] = storage
    app.extensions["debate_orchestrator"] = debate_orchestrator
    app.extensions["news_feed_service"] = news_feed_service
    app.extensions["fact_referee_service"] = fact_referee_service

    @app.before_request
    def attach_request_metadata() -> None:
        g.request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        g.request_started_at = time.perf_counter()

    @app.after_request
    def inject_request_id(response):
        response.headers["X-Request-ID"] = g.request_id
        duration_ms = (time.perf_counter() - g.request_started_at) * 1000
        logging.info(
            "request_id=%s method=%s path=%s status=%s duration_ms=%.2f",
            g.request_id,
            request.method,
            request.path,
            response.status_code,
            duration_ms,
        )
        return response

    app.register_blueprint(debate_bp)
    app.register_blueprint(news_bp)

    @app.get("/")
    def index() -> Any:
        return send_from_directory(FRONTEND_BUILD_DIR, "index.html")

    @app.get("/health")
    def health() -> Any:
        return jsonify({"status": "ok"})

    @app.errorhandler(AppError)
    def handle_app_error(error: AppError):
        payload = {
            "error": {
                "code": error.code,
                "message": error.message,
                "request_id": getattr(g, "request_id", None),
            }
        }
        if error.details is not None:
            payload["error"]["details"] = error.details
        return jsonify(payload), error.status_code

    @app.errorhandler(ConfigurationError)
    def handle_config_error(error: ConfigurationError):
        payload = {
            "error": {
                "code": error.code,
                "message": error.message,
                "request_id": getattr(g, "request_id", None),
            }
        }
        return jsonify(payload), error.status_code

    @app.errorhandler(HTTPException)
    def handle_http_exception(error: HTTPException):
        payload = {
            "error": {
                "code": "http_error",
                "message": error.description,
                "request_id": getattr(g, "request_id", None),
            }
        }
        return jsonify(payload), error.code

    @app.errorhandler(Exception)
    def handle_unexpected_error(error: Exception):
        logging.exception(
            "request_id=%s unexpected_error=%s",
            getattr(g, "request_id", None),
            str(error),
        )
        payload = {
            "error": {
                "code": "internal_error",
                "message": "Unexpected internal server error",
                "request_id": getattr(g, "request_id", None),
            }
        }
        return jsonify(payload), 500

    return app


def _configure_logging(log_level: str) -> None:
    level = getattr(logging, log_level.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(message)s",
    )


app = create_app()
