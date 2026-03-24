from __future__ import annotations

from fastapi import APIRouter, Request, Response
from pydantic import BaseModel

from .session_store import SessionStore

router = APIRouter(prefix="/api/game", tags=["game"])

store = SessionStore()
SESSION_COOKIE_NAME = "ristiseiska_session"


class PlayCardRequest(BaseModel):
    card_id: str


class GiveCardRequest(BaseModel):
    card_id: str


class ContinueRequest(BaseModel):
    continue_choice: bool


def _read_session_id(request: Request) -> str | None:
    return request.cookies.get(SESSION_COOKIE_NAME)


def _set_session_cookie(response: Response, session_id: str, secure: bool):
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=session_id,
        httponly=True,
        samesite="lax",
        secure=secure,
        max_age=60 * 60 * 12,
        path="/",
    )

def _get_existing_manager(request: Request):
    session_id = _read_session_id(request)
    print("SESSION READ:", session_id)

    if not session_id:
        return None

    return store.get(session_id)

@router.post("/new")
def new_game(request: Request, response: Response):
    session_id = _read_session_id(request)
    print("NEW session before:", session_id)

    if not session_id:
        session_id = store.create_session_id()
        is_https = request.url.scheme == "https"
        _set_session_cookie(response, session_id, secure=is_https)
        print("NEW session created:", session_id, "secure:", is_https)

    manager = store.get_or_create(session_id)
    return manager.new_game()


@router.get("/state")
def get_state(request: Request):
    session_id = _read_session_id(request)
    print("STATE session:", session_id)

    manager = _get_existing_manager(request)
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
def play_card(req: PlayCardRequest, request: Request):
    session_id = _read_session_id(request)
    print("PLAY session:", session_id)

    manager = _get_existing_manager(request)
    if manager is None:
        return {"error": "no game"}

    return manager.play_card(req.card_id)


@router.post("/give")
def give_card(req: GiveCardRequest, request: Request):
    session_id = _read_session_id(request)
    print("GIVE session:", session_id)

    manager = _get_existing_manager(request)
    if manager is None:
        return {"error": "no game"}

    return manager.give_card(req.card_id)


@router.post("/continue")
def choose_continuation(req: ContinueRequest, request: Request):
    session_id = _read_session_id(request)
    print("CONTINUE session:", session_id)

    manager = _get_existing_manager(request)
    if manager is None:
        return {"error": "no game"}

    return manager.choose_continuation(req.continue_choice)


@router.post("/advance")
def advance_ai(request: Request):
    session_id = _read_session_id(request)
    print("ADVANCE session:", session_id)

    manager = _get_existing_manager(request)
    if manager is None:
        return {"error": "no game"}

    return manager.advance_ai()