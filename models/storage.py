from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any


class Storage:
    """Minimal JSON-file persistence for hackathon MVP."""

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()

    def init_db(self) -> None:
        if not self.db_path.exists():
            self._save({"conversations": {}})

    def create_conversation(
        self,
        conversation_id: str,
        topic: str,
        language: str,
        status: str,
        meta: dict[str, Any],
    ) -> None:
        created_at = datetime.now(timezone.utc).isoformat()
        store = self._load()
        conversations = store.setdefault("conversations", {})
        conversations[conversation_id] = {
            "conversation_id": conversation_id,
            "topic": topic,
            "language": language,
            "status": status,
            "created_at": created_at,
            "meta": meta,
            "turns": [],
        }
        self._save(store)

    def update_conversation(
        self, conversation_id: str, status: str, meta: dict[str, Any]
    ) -> None:
        store = self._load()
        conversation = store.get("conversations", {}).get(conversation_id)
        if conversation is None:
            return
        conversation["status"] = status
        conversation["meta"] = meta
        self._save(store)

    def add_turn(
        self,
        conversation_id: str,
        turn_index: int,
        speaker: str,
        text: str,
        audio_path: str | None,
        latency_ms: float | None,
        request_id: str,
        raw_meta: dict[str, Any] | None,
    ) -> None:
        created_at = datetime.now(timezone.utc).isoformat()
        store = self._load()
        conversation = store.get("conversations", {}).get(conversation_id)
        if conversation is None:
            return

        turns = conversation.setdefault("turns", [])
        turns = [turn for turn in turns if turn.get("turn_index") != turn_index]
        turns.append(
            {
                "turn_index": turn_index,
                "speaker": speaker,
                "text": text,
                "audio_path": audio_path,
                "latency_ms": latency_ms,
                "request_id": request_id,
                "raw_meta": raw_meta,
                "created_at": created_at,
            }
        )
        turns.sort(key=lambda item: int(item["turn_index"]))
        conversation["turns"] = turns
        self._save(store)

    def get_conversation(self, conversation_id: str) -> dict[str, Any] | None:
        store = self._load()
        conversation = store.get("conversations", {}).get(conversation_id)
        if conversation is None:
            return None
        return {
            "conversation_id": conversation["conversation_id"],
            "topic": conversation["topic"],
            "language": conversation["language"],
            "status": conversation["status"],
            "created_at": conversation["created_at"],
            "meta": conversation.get("meta", {}),
            "turns": list(conversation.get("turns", [])),
        }

    def get_turn_audio_path(self, conversation_id: str, turn_index: int) -> str | None:
        conversation = self.get_conversation(conversation_id)
        if conversation is None:
            return None
        for turn in conversation.get("turns", []):
            if int(turn.get("turn_index", -1)) == turn_index:
                return turn.get("audio_path")
        return None

    def _load(self) -> dict[str, Any]:
        with self._lock:
            if not self.db_path.exists():
                return {"conversations": {}}
            try:
                return json.loads(self.db_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                return {"conversations": {}}

    def _save(self, store: dict[str, Any]) -> None:
        with self._lock:
            temp_path = self.db_path.with_suffix(self.db_path.suffix + ".tmp")
            temp_path.write_text(
                json.dumps(store, ensure_ascii=True, indent=2), encoding="utf-8"
            )
            temp_path.replace(self.db_path)
