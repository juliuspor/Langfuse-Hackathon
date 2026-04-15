from __future__ import annotations

from pathlib import Path

import pytest

from app import create_app
from models.storage import Storage
from services.debate_orchestrator import DebateOrchestrator
from services.news_context import NewsContextService
from utils.config import Settings
from utils.errors import ExternalServiceError


class FakeElevenLabsClient:
    def __init__(self) -> None:
        self.simulate_calls: list[str] = []
        self.simulate_requests: list[dict] = []
        self.turn_texts: list[str] = []
        self.tts_calls: list[str] = []
        self.fail_tts_on_turn: int | None = None

    def simulate_turn(
        self, *, agent_id: str, partial_history: list[dict], language: str
    ) -> dict:
        self.simulate_calls.append(agent_id)
        self.simulate_requests.append(
            {
                "agent_id": agent_id,
                "partial_history": list(partial_history),
                "language": language,
            }
        )
        turn_no = len(self.simulate_calls)
        if turn_no <= len(self.turn_texts):
            text = self.turn_texts[turn_no - 1]
        else:
            text = f"Turn {turn_no} statement. Follow-up sentence for natural flow."
        return {
            "text": text,
            "latency_ms": 12.0,
            "analysis": {"ok": True},
            "raw": {
                "simulated_conversation": [
                    {
                        "role": "agent",
                        "message": text,
                        "time_in_call_secs": turn_no,
                    }
                ]
            },
        }

    def synthesize_speech(self, *, voice_id: str, text: str, language: str) -> dict:
        self.tts_calls.append(voice_id)
        turn_no = len(self.tts_calls)
        if self.fail_tts_on_turn == turn_no:
            raise ExternalServiceError("synthetic tts failure")
        return {
            "audio_bytes": b"ID3fake-mp3",
            "latency_ms": 7.0,
            "headers": {},
        }


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        elevenlabs_api_key="test-key",
        elevenlabs_agent_1_id="agent_1",
        elevenlabs_agent_2_id="agent_2",
        elevenlabs_voice_1_id="voice_1",
        elevenlabs_voice_2_id="voice_2",
        elevenlabs_base_url="https://api.elevenlabs.io",
        news_api_key=None,
        database_path=tmp_path / "debates.json",
        audio_storage_dir=tmp_path / "audio",
        request_timeout_seconds=10.0,
        tts_model_id="eleven_flash_v2_5",
        tts_output_format="mp3_44100_128",
        tts_optimize_streaming_latency=0,
        max_turns=20,
        log_level="INFO",
    )


@pytest.fixture
def storage(settings: Settings) -> Storage:
    db = Storage(settings.database_path)
    db.init_db()
    return db


@pytest.fixture
def fake_elevenlabs_client() -> FakeElevenLabsClient:
    return FakeElevenLabsClient()


@pytest.fixture
def orchestrator(
    settings: Settings, storage: Storage, fake_elevenlabs_client: FakeElevenLabsClient
) -> DebateOrchestrator:
    return DebateOrchestrator(
        settings=settings,
        storage=storage,
        elevenlabs_client=fake_elevenlabs_client,
        news_context_service=NewsContextService(),
    )


@pytest.fixture
def app_client(
    settings: Settings, storage: Storage, fake_elevenlabs_client: FakeElevenLabsClient
):
    app = create_app(
        {
            "TESTING": True,
            "SETTINGS": settings,
            "STORAGE": storage,
            "ELEVENLABS_CLIENT": fake_elevenlabs_client,
        }
    )
    with app.test_client() as client:
        yield client
