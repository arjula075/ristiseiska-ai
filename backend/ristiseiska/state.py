from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from .cards import Card, Suit, deal, card_7_of_clubs
from .game import starting_player
from .ranks import below_from_7, above_from_7


@dataclass(slots=True)
class TableState:
    """
    Per suit we keep bounds (low, high) anchored at 7.

    House rule phases per suit:
      - not started -> only 7
      - (7,7) -> only 6 allowed
      - (6,7) -> only 8 allowed
      - (6,8) and beyond -> normal expansion down/up
    """
    bounds: dict[Suit, Optional[tuple[int, int]]] = field(default_factory=lambda: {s: None for s in Suit})
    played: dict[Suit, set[int]] = field(default_factory=lambda: {s: set() for s in Suit})

    def can_play(self, card: Card) -> bool:
        b = self.bounds[card.suit]

        if b is None:
            return card.rank == 7

        low, high = b

        # Phase 1: only 7
        if low == 7 and high == 7:
            return card.rank == 6

        # Phase 2: 7+6
        if low == 6 and high == 7:
            return card.rank == 8

        # Phase 3+: open both directions
        need_down = below_from_7(low)
        need_up = above_from_7(high)
        return (
                (need_down is not None and card.rank == need_down)
                or (need_up is not None and card.rank == need_up)
        )

    def add(self, card: Card) -> None:
        if not self.can_play(card):
            raise ValueError(f"Illegal card on table now: {card}")

        b = self.bounds[card.suit]
        if b is None:
            # must be 7
            self.bounds[card.suit] = (7, 7)
        else:
            low, high = b

            # phase updates
            if low == 7 and high == 7:
                # must be 6
                low = 6
            elif low == 6 and high == 7:
                # must be 8
                high = 8
            else:
                # normal expansion
                if card.rank == below_from_7(low):
                    low = card.rank
                elif card.rank == above_from_7(high):
                    high = card.rank
                else:
                    raise ValueError(f"Internal error: card {card} not matching expected next ranks")

            self.bounds[card.suit] = (low, high)

        self.played[card.suit].add(card.rank)

    def has(self, card: Card) -> bool:
        return card.rank in self.played[card.suit]


@dataclass(slots=True)
class GameState:
    hands: List[List[Card]]
    table: TableState
    turn: int
    starter: int
    placements: List[int] = field(default_factory=list)
    pending_give_from: Optional[int] = None
    pending_give_to: Optional[int] = None

    done: bool = False
    loser: Optional[int] = None

    @property
    def num_players(self) -> int:
        return len(self.hands)


def reset(seed: int | None = None, num_players: int = 4) -> GameState:
    """
    Fresh game:
      - deterministic deal(seed)
      - find starter who holds 7♣
      - force-play 7♣ to table
      - turn moves to next player after starter
    """
    if num_players != 4:
        raise ValueError("For now, reset supports only 4 players.")

    hands = deal(num_players=num_players, seed=seed)
    sp = starting_player(hands)

    seven_clubs = card_7_of_clubs()
    hands[sp].remove(seven_clubs)

    table = TableState()
    table.add(seven_clubs)

    turn = (sp + 1) % num_players
    return GameState(hands=hands, table=table, turn=turn, starter=sp)
