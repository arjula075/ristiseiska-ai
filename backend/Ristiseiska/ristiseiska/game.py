from __future__ import annotations
from typing import List
from .cards import Card, card_7_of_clubs

def starting_player(hands: List[List[Card]]) -> int:
    target = card_7_of_clubs()
    for i, hand in enumerate(hands):
        if target in hand:
            return i
    raise ValueError("7♣ not found in any hand (invalid deal)")
