from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from .game_manager import GameManager

router = APIRouter(prefix="/api/game", tags=["game"])

manager = GameManager()


class PlayCardRequest(BaseModel):
    card_id: str


class GiveCardRequest(BaseModel):
    card_id: str


class ContinueRequest(BaseModel):
    continue_choice: bool


@router.post("/new")
def new_game():
    return manager.new_game()


@router.get("/state")
def get_state():
    return manager.get_public_state()


@router.post("/play")
def play_card(req: PlayCardRequest):
    return manager.play_card(req.card_id)


@router.post("/give")
def give_card(req: GiveCardRequest):
    return manager.give_card(req.card_id)


@router.post("/continue")
def choose_continuation(req: ContinueRequest):
    return manager.choose_continuation(req.continue_choice)


@router.post("/advance")
def advance_ai():
    return manager.advance_ai()