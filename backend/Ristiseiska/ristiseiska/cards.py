from __future__ import annotations
from dataclasses import dataclass
from enum import IntEnum
from typing import List, Sequence
import random


class Suit(IntEnum):
    CLUBS = 0
    DIAMONDS = 1
    HEARTS = 2
    SPADES = 3


# Rank as int: 2..14 where 11=J, 12=Q, 13=K, 14=A
RANK_STR = {
    2: "2", 3: "3", 4: "4", 5: "5", 6: "6", 7: "7", 8: "8", 9: "9", 10: "10",
    11: "J", 12: "Q", 13: "K", 14: "A",
}
SUIT_STR = {
    Suit.CLUBS: "♣",
    Suit.DIAMONDS: "♦",
    Suit.HEARTS: "♥",
    Suit.SPADES: "♠",
}


@dataclass(frozen=True, slots=True, order=True)
class Card:
    """
    Order is lexicographic by (suit, rank) because of dataclass(order=True).
    If you later want a different ordering (e.g., rank-first), change field order.
    """
    suit: Suit
    rank: int  # 2..14

    def __post_init__(self) -> None:
        if not isinstance(self.suit, Suit):
            raise TypeError(f"suit must be Suit, got {type(self.suit)}")
        if self.rank not in RANK_STR:
            raise ValueError(f"rank must be in 2..14, got {self.rank}")

    @property
    def suit_id(self) -> int:
        return int(self.suit)

    @property
    def rank_id(self) -> int:
        return int(self.rank)

    def short(self) -> str:
        return f"{RANK_STR[self.rank]}{SUIT_STR[self.suit]}"

    def __str__(self) -> str:
        return self.short()

    def __repr__(self) -> str:
        return f"Card({self.short()})"


def standard_deck() -> List[Card]:
    """Return a fresh 52-card deck in a deterministic canonical order."""
    return [Card(suit, rank) for suit in Suit for rank in range(2, 15)]


def card_7_of_clubs() -> Card:
    return Card(Suit.CLUBS, 7)


# --- Tiny self-test / demo ---
if __name__ == "__main__":
    deck = standard_deck()
    assert len(deck) == 52
    assert len(set(deck)) == 52  # hashable, no duplicates
    assert card_7_of_clubs() in deck

    print("First 5:", deck[:5])
    print("7♣:", card_7_of_clubs(), "suit_id=", card_7_of_clubs().suit_id, "rank_id=", card_7_of_clubs().rank_id)


def deal(num_players: int = 4, seed: int | None = None) -> List[List[Card]]:
    """
    Deal a full 52-card deck evenly to num_players.
    For 4 players -> 13 cards each.
    Deterministic given the same seed.
    """
    deck = standard_deck()
    rng = random.Random(seed)
    rng.shuffle(deck)

    if len(deck) % num_players != 0:
        raise ValueError("Deck size must be divisible by num_players")

    hand_size = len(deck) // num_players
    hands = [deck[i * hand_size:(i + 1) * hand_size] for i in range(num_players)]

    # Optional: sort hands for easier debugging (canonical order)
    for h in hands:
        h.sort()

    return hands
