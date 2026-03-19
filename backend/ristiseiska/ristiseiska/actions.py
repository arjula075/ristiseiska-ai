from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .cards import Card, Suit
from .moves import Action

# Action space (fixed):
# 0..51      PLAY(card, cont=False)
# 52..103    PLAY(card, cont=True)
# 104        REQUEST
# 105..156   GIVE(card)
ACTION_DIM = 157
REQUEST_ID = 104
GIVE_BASE = 105

# Card id mapping: suit * 13 + rank_index, where rank_index: 2..14 -> 0..12
_RANKS = list(range(2, 15))  # 2..14 (A)
_RANK_TO_IDX = {r: i for i, r in enumerate(_RANKS)}
_IDX_TO_RANK = {i: r for r, i in _RANK_TO_IDX.items()}


def card_to_id(card: Card) -> int:
    ri = _RANK_TO_IDX[card.rank]
    return int(card.suit) * 13 + ri


def id_to_card(card_id: int) -> Card:
    if not (0 <= card_id < 52):
        raise ValueError(f"card_id out of range: {card_id}")
    suit = Suit(card_id // 13)
    ri = card_id % 13
    rank = _IDX_TO_RANK[ri]
    return Card(suit, rank)


def encode_action(action: Action) -> int:
    if action.kind == "REQUEST":
        return REQUEST_ID

    if action.kind == "PLAY":
        if action.card is None:
            raise ValueError("PLAY requires card")
        cid = card_to_id(action.card)
        return cid + (52 if action.cont else 0)

    if action.kind == "GIVE":
        if action.card is None:
            raise ValueError("GIVE requires card")
        cid = card_to_id(action.card)
        return GIVE_BASE + cid

    raise ValueError(f"Unknown action kind: {action.kind}")


def decode_action(action_id: int) -> Action:
    if action_id == REQUEST_ID:
        return Action("REQUEST")

    if 0 <= action_id < 52:
        return Action("PLAY", id_to_card(action_id), cont=False)

    if 52 <= action_id < 104:
        return Action("PLAY", id_to_card(action_id - 52), cont=True)

    if GIVE_BASE <= action_id < ACTION_DIM:
        return Action("GIVE", id_to_card(action_id - GIVE_BASE))

    raise ValueError(f"action_id out of range: {action_id}")
