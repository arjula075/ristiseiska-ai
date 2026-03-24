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


def get_session_id(request: Request, response: Response) -> str:
    session_id = request.cookies.get(SESSION_COOKIE_NAME)

    if not session_id:
        session_id = store.create_session_id()
        response.set_cookie(
            key=SESSION_COOKIE_NAME,
            value=session_id,
            httponly=True,
            samesite="lax",
            secure=True,   # Renderissä https
            max_age=60 * 60 * 12,
        )

    return session_id


def get_manager(request: Request, response: Response):
    session_id = get_session_id(request, response)
    return store.get_or_create(session_id)


@router.post("/new")
def new_game(request: Request, response: Response):
    return get_manager(request, response).new_game()


@router.get("/state")
def get_state(request: Request, response: Response):
    return get_manager(request, response).get_public_state()


@router.post("/play")
def play_card(req: PlayCardRequest, request: Request, response: Response):
    return get_manager(request, response).play_card(req.card_id)


@router.post("/give")
def give_card(req: GiveCardRequest, request: Request, response: Response):
    return get_manager(request, response).give_card(req.card_id)


@router.post("/continue")
def choose_continuation(req: ContinueRequest, request: Request, response: Response):
    return get_manager(request, response).choose_continuation(req.continue_choice)


@router.post("/advance")
def advance_ai(request: Request, response: Response):
    return get_manager(request, response).advance_ai()