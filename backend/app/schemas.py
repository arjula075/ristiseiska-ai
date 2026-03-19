from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, Field


UiMode = Literal["PLAY", "GIVE", "CONTINUE", "AI_THINKING", "GAME_OVER", "NO_GAME"]
GameStatus = Literal["active", "game_over", "no_game"]


class CardView(BaseModel):
    id: str
    suit: str
    rank: int
    label: str


class OpponentView(BaseModel):
    player: int
    cards: int
    is_active: bool = False


class RequestContext(BaseModel):
    asking_player: int | None = None
    target_player: int | None = None
    message: str | None = None


class ContinuationContext(BaseModel):
    available: bool = False
    message: str | None = None


class TableSuitView(BaseModel):
    suit: str
    cards: list[int] = Field(default_factory=list)


class TableView(BaseModel):
    suits: list[TableSuitView] = Field(default_factory=list)


class PublicGameState(BaseModel):
    game_status: GameStatus
    ui_mode: UiMode
    active_player: int | None = None
    human_player: int = 0
    human_hand: list[CardView] = Field(default_factory=list)
    opponents: list[OpponentView] = Field(default_factory=list)
    table: TableView = Field(default_factory=TableView)
    request_context: RequestContext = Field(default_factory=RequestContext)
    continuation_context: ContinuationContext = Field(default_factory=ContinuationContext)
    recent_events: list[str] = Field(default_factory=list)
    error_message: str | None = None


class CardActionRequest(BaseModel):
    card_id: str


class ContinueRequest(BaseModel):
    continue_choice: bool