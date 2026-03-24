from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, Optional
from uuid import uuid4

from .game_manager import GameManager

SESSION_TTL = timedelta(hours=12)


@dataclass
class SessionEntry:
    manager: GameManager
    last_seen: datetime


class SessionStore:
    def __init__(self):
        self._sessions: Dict[str, SessionEntry] = {}

    def get(self, session_id: str) -> Optional[GameManager]:
        now = datetime.utcnow()
        self.cleanup()

        entry = self._sessions.get(session_id)
        if entry is None:
            return None

        entry.last_seen = now
        return entry.manager

    def create(self, session_id: str) -> GameManager:
        now = datetime.utcnow()
        self.cleanup()

        manager = GameManager()
        self._sessions[session_id] = SessionEntry(
            manager=manager,
            last_seen=now,
        )
        return manager

    def get_or_create(self, session_id: str) -> GameManager:
        existing = self.get(session_id)
        if existing is not None:
            return existing
        return self.create(session_id)

    def create_session_id(self) -> str:
        return uuid4().hex

    def cleanup(self):
        now = datetime.utcnow()
        expired = [
            sid
            for sid, entry in self._sessions.items()
            if now - entry.last_seen > SESSION_TTL
        ]
        for sid in expired:
            del self._sessions[sid]