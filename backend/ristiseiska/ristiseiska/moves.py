from __future__ import annotations
from dataclasses import dataclass
from typing import List, Literal, Optional

from .cards import Card
from .state import TableState, GameState


def legal_plays(hand: List[Card], table: TableState) -> List[Card]:
    return [c for c in hand if table.can_play(c)]


def is_end_rank(rank: int) -> bool:
    # King=13, Ace=14
    return rank in (13, 14)


ActionType = Literal["PLAY", "REQUEST", "GIVE"]


@dataclass(frozen=True, slots=True)
class Action:
    kind: ActionType
    card: Optional[Card] = None
    cont: bool = False  # <-- continuation flag (only meaningful for PLAY)


def available_actions(state: GameState, player: int) -> List[Action]:
    """
    Phase rules:
      - If GIVE pending: only pending_give_from can act, must GIVE any card.
      - Otherwise normal turn:
          - if legal plays exist: PLAY actions
              - if card is A or K, offer cont=True as additional option
          - else: REQUEST
    """
    # GIVE phase
    if state.pending_give_from is not None:
        if player != state.pending_give_from:
            return []
        playable = legal_plays(state.hands[player], state.table)
        non_playable = [c for c in state.hands[player] if c not in playable]

        if non_playable:
            return [Action("GIVE", c) for c in non_playable]
        return [Action("GIVE", c) for c in state.hands[player]]

    # Normal phase
    plays = legal_plays(state.hands[player], state.table)

    if plays:
        actions: List[Action] = []
        for c in plays:
            actions.append(Action("PLAY", c, cont=False))

            if is_end_rank(c.rank):
                # Offer cont=True only if a legal follow-up PLAY exists immediately after
                if _can_continue_after_play(state, player, c):
                    actions.append(Action("PLAY", c, cont=True))
        return actions

    return [Action("REQUEST")]


def _can_continue_after_play(state: GameState, player: int, card: Card) -> bool:
    # Quick simulation using a lightweight table copy
    import copy
    table_copy = copy.deepcopy(state.table)

    if not table_copy.can_play(card):
        return False

    # remove one instance of card from hand
    hand_copy = state.hands[player].copy()
    try:
        hand_copy.remove(card)
    except ValueError:
        return False

    table_copy.add(card)
    return len(legal_plays(hand_copy, table_copy)) > 0

