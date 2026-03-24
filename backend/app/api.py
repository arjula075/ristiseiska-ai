from __future__ import annotations

from fastapi import APIRouter, Header
from pydantic import BaseModel

from .session_store import SessionStore

router = APIRouter(prefix="/api/game", tags=["game"])

store = SessionStore()


class PlayCardRequest(BaseModel):
    card_id: str


class GiveCardRequest(BaseModel):
    card_id: str


class ContinueRequest(BaseModel):
    continue_choice: bool


def _get_existing_manager(session_id: str | None):
    if not session_id:
        return None
    return store.get(session_id)


@router.post("/new")
def new_game():
    session_id = store.create_session_id()
    manager = store.create(session_id)
    state = manager.new_game()

    return {
        "session_id": session_id,
        "state": state,
    }


@router.get("/state")
def get_state(x_session_id: str | None = Header(default=None)):
    manager = _get_existing_manager(x_session_id)
    if manager is None:
        return {
            "game_status": "no_game",
            "ui_mode": "NO_GAME",
            "active_player": None,
            "human_player": 0,
            "human_hand": [],
            "opponents": [],
            "table": {"suits": []},
            "pending_continuation": False,
            "pending_play_card_id": None,
            "recent_events": [],
            "error": None,
        }

    return manager.get_public_state()


@router.post("/play")
def play_card(req: PlayCardRequest, x_session_id: str | None = Header(default=None)):
    manager = _get_existing_manager(x_session_id)
    if manager is None:
        return {"error": "no game"}
    return manager.play_card(req.card_id)


@router.post("/give")
def give_card(req: GiveCardRequest, x_session_id: str | None = Header(default=None)):
    manager = _get_existing_manager(x_session_id)
    if manager is None:
        return {"error": "no game"}
    return manager.give_card(req.card_id)


@router.post("/continue")
def choose_continuation(
        req: ContinueRequest,
        x_session_id: str | None = Header(default=None),
):
    manager = _get_existing_manager(x_session_id)
    if manager is None:
        return {"error": "no game"}
    return manager.choose_continuation(req.continue_choice)


@router.post("/advance")
def advance_ai(x_session_id: str | None = Header(default=None)):
    manager = _get_existing_manager(x_session_id)
    if manager is None:
        return {"error": "no game"}
    return manager.advance_ai()