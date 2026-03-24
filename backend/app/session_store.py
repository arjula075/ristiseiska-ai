from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict
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

    def get_or_create(self, session_id: str) -> GameManager:
        now = datetime.utcnow()
        self.cleanup()

        if session_id not in self._sessions:
            self._sessions[session_id] = SessionEntry(
                manager=GameManager(),
                last_seen=now,
            )
        else:
            self._sessions[session_id].last_seen = now

        return self._sessions[session_id].manager

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