from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/api/game", tags=["game"])


def get_manager():
    global _manager
    try:
        return _manager
    except NameError:
        from .game_manager import GameManager   # 👈 SIIRRETTY TÄNNE

        _manager = GameManager()
        return _manager


class PlayCardRequest(BaseModel):
    card_id: str


class GiveCardRequest(BaseModel):
    card_id: str


class ContinueRequest(BaseModel):
    continue_choice: bool


@router.post("/new")
def new_game():
    return get_manager().new_game()


@router.get("/state")
def get_state():
    return get_manager().get_public_state()


@router.post("/play")
def play_card(req: PlayCardRequest):
    return get_manager().play_card(req.card_id)


@router.post("/give")
def give_card(req: GiveCardRequest):
    return get_manager().give_card(req.card_id)


@router.post("/continue")
def choose_continuation(req: ContinueRequest):
    return get_manager().choose_continuation(req.continue_choice)


@router.post("/advance")
def advance_ai():
    return get_manager().advance_ai()