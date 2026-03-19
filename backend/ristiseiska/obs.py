from __future__ import annotations

from functools import lru_cache

import numpy as np

from .actions import card_to_id
from .cards import Suit
from .moves import legal_plays
from .ranks import below_from_7, above_from_7
from .state import GameState


# Observation layout
#
# hand_onehot[52]
# card_deadness[52]
# table per suit: [started, low_idx, high_idx] * 4  => 12
# turn onehot[4]
# pending: [flag, from_onehot4, to_onehot4] => 9
# hand_sizes[4]
# placed_flags[4]
# own_playable_count[1]
# own_suit_counts[4]
# own_end_rank_counts[4]
# own_singleton_counts[4]
# own_middle_counts[4]
# own_playable_now_count[4]
# own_one_step_away_count[4]
# own_path_potential[4]
# board_control_global[4]
# board_control_per_suit[8]
# open7_followup_depth[4]
#
# total = 182
OBS_DIM = 182


def _rank_to_idx_1based(rank: int) -> float:
    return float((rank - 2) + 1)


def _rel_index(observer: int, absolute_player: int, num_players: int) -> int:
    return (absolute_player - observer) % num_players


def _abs_from_rel(observer: int, rel_player: int, num_players: int) -> int:
    return (observer + rel_player) % num_players


def _needed_ranks_from_bounds(bounds: tuple[int, int] | None) -> tuple[int, ...]:
    if bounds is None:
        return (7,)

    low, high = bounds

    if low == 7 and high == 7:
        return (6,)

    if low == 6 and high == 7:
        return (8,)

    needed = []
    need_down = below_from_7(low)
    need_up = above_from_7(high)

    if need_down is not None:
        needed.append(need_down)
    if need_up is not None:
        needed.append(need_up)

    return tuple(needed)


def _advance_bounds(bounds: tuple[int, int] | None, rank: int) -> tuple[int, int]:
    if bounds is None:
        return (7, 7)

    low, high = bounds

    if low == 7 and high == 7:
        return (6, 7)

    if low == 6 and high == 7:
        return (6, 8)

    need_down = below_from_7(low)
    need_up = above_from_7(high)

    if need_down is not None and rank == need_down:
        return (rank, high)

    if need_up is not None and rank == need_up:
        return (low, rank)

    raise ValueError(f"Illegal rank {rank} for bounds {bounds}")


@lru_cache(maxsize=None)
def _suit_deadness(rank: int, bounds: tuple[int, int] | None) -> int:
    """
    Deterministic board-distance in suit-steps until the rank becomes playable.
    0 = playable now
    1 = one legal suit-advance away
    ...
    """
    needed = _needed_ranks_from_bounds(bounds)
    if rank in needed:
        return 0

    candidates = [_advance_bounds(bounds, r) for r in needed]
    if not candidates:
        return 13

    return 1 + min(_suit_deadness(rank, nxt) for nxt in candidates)


def _card_deadness_feature(card, bounds: tuple[int, int] | None) -> float:
    return _suit_deadness(card.rank, bounds) / 13.0


def _own_suit_structure_features(hand, suit: Suit) -> tuple[float, float, float]:
    """
    Returns normalized counts in this suit:
      - end_rank_count: number of A/K cards
      - singleton_count: cards with 0 adjacent same-suit neighbors in hand
      - middle_count: cards with 2 adjacent same-suit neighbors in hand
    """
    suit_cards = [c for c in hand if c.suit == suit]
    rank_set = {c.rank for c in suit_cards}

    end_rank_count = 0
    singleton_count = 0
    middle_count = 0

    for c in suit_cards:
        if c.rank in (13, 14):
            end_rank_count += 1

        neighbors = 0
        if (c.rank - 1) in rank_set:
            neighbors += 1
        if (c.rank + 1) in rank_set:
            neighbors += 1

        if neighbors == 0:
            singleton_count += 1
        elif neighbors == 2:
            middle_count += 1

    return (
        end_rank_count / 13.0,
        singleton_count / 13.0,
        middle_count / 13.0,
    )


def _board_aware_suit_features(hand, suit: Suit, bounds: tuple[int, int] | None) -> tuple[float, float, float]:
    """
    Returns normalized per-suit features:
      - playable_now_count
      - one_step_away_count
      - path_potential
    """
    suit_ranks = tuple(sorted(c.rank for c in hand if c.suit == suit))
    rank_set = set(suit_ranks)

    needed_now = _needed_ranks_from_bounds(bounds)
    playable_now_count = sum(1 for r in needed_now if r in rank_set)

    one_step_ranks = set()
    for r in needed_now:
        next_bounds = _advance_bounds(bounds, r)
        for nxt in _needed_ranks_from_bounds(next_bounds):
            one_step_ranks.add(nxt)

    one_step_away_count = sum(1 for r in one_step_ranks if r in rank_set)

    @lru_cache(maxsize=None)
    def best_chain(cur_bounds: tuple[int, int] | None, remaining_ranks: tuple[int, ...]) -> int:
        remaining = set(remaining_ranks)
        needed = _needed_ranks_from_bounds(cur_bounds)

        best = 0
        for r in needed:
            if r in remaining:
                nxt_bounds = _advance_bounds(cur_bounds, r)
                nxt_remaining = tuple(x for x in remaining_ranks if x != r)
                best = max(best, 1 + best_chain(nxt_bounds, nxt_remaining))
        return best

    path_potential = best_chain(bounds, suit_ranks)

    return (
        playable_now_count / 13.0,
        one_step_away_count / 13.0,
        path_potential / 13.0,
    )


def _open_slot_stats_for_suit(hand, suit: Suit, bounds: tuple[int, int] | None) -> tuple[int, int]:
    needed = _needed_ranks_from_bounds(bounds)
    rank_set = {c.rank for c in hand if c.suit == suit}

    open_slots = len(needed)
    own_open_slots = sum(1 for r in needed if r in rank_set)

    return open_slots, own_open_slots


def _open7_followup_depth(hand, suit: Suit, bounds: tuple[int, int] | None) -> float:
    """
    If suit is unopened and player has 7 of this suit, return how many immediate
    downward follow-up cards exist in hand: 6,5,4,3,2,A.
    Otherwise 0.

    Examples:
      7           -> 0
      7,6         -> 1
      7,6,5,4     -> 3
      7,6,5,4,3,2,A -> 6
    """
    if bounds is not None:
        return 0.0

    rank_set = {c.rank for c in hand if c.suit == suit}
    if 7 not in rank_set:
        return 0.0

    depth = 0
    follow_order = [6, 5, 4, 3, 2, 14]  # A as terminal below 2 in this game's chain logic
    for r in follow_order:
        if r in rank_set:
            depth += 1
        else:
            break

    return depth / 6.0


def observe(state: GameState, player: int) -> np.ndarray:
    x = np.zeros((OBS_DIM,), dtype=np.float32)

    k = 0
    n = state.num_players
    hand = state.hands[player]

    # hand one-hot [52]
    for c in hand:
        x[k + card_to_id(c)] = 1.0
    k += 52

    # card deadness [52]
    for c in hand:
        x[k + card_to_id(c)] = _card_deadness_feature(c, state.table.bounds[c.suit])
    k += 52

    # table bounds [12]
    for s in [Suit.CLUBS, Suit.DIAMONDS, Suit.HEARTS, Suit.SPADES]:
        b = state.table.bounds[s]

        if b is None:
            started = 0.0
            low = 0.0
            high = 0.0
        else:
            started = 1.0
            low_rank, high_rank = b
            low = _rank_to_idx_1based(low_rank)
            high = _rank_to_idx_1based(high_rank)

        x[k + 0] = started
        x[k + 1] = low
        x[k + 2] = high
        k += 3

    # turn one-hot [4]
    rel_turn = _rel_index(player, state.turn, n)
    for i in range(n):
        x[k + i] = 1.0 if i == rel_turn else 0.0
    k += 4

    # pending give [9]
    pending = 1.0 if state.pending_give_from is not None else 0.0
    x[k] = pending
    k += 1

    rel_from = None if state.pending_give_from is None else _rel_index(player, state.pending_give_from, n)
    for i in range(n):
        x[k + i] = 1.0 if rel_from == i else 0.0
    k += 4

    rel_to = None if state.pending_give_to is None else _rel_index(player, state.pending_give_to, n)
    for i in range(n):
        x[k + i] = 1.0 if rel_to == i else 0.0
    k += 4

    # hand sizes [4]
    for rel_i in range(n):
        abs_i = _abs_from_rel(player, rel_i, n)
        x[k + rel_i] = len(state.hands[abs_i]) / 13.0
    k += 4

    # placed flags [4]
    placed = set(state.placements)
    for rel_i in range(n):
        abs_i = _abs_from_rel(player, rel_i, n)
        x[k + rel_i] = 1.0 if abs_i in placed else 0.0
    k += 4

    # own playable count [1]
    x[k] = len(legal_plays(hand, state.table)) / 13.0
    k += 1

    # own suit counts [4]
    for s in [Suit.CLUBS, Suit.DIAMONDS, Suit.HEARTS, Suit.SPADES]:
        x[k] = sum(1 for c in hand if c.suit == s) / 13.0
        k += 1

    # own end/singleton/middle [12]
    for s in [Suit.CLUBS, Suit.DIAMONDS, Suit.HEARTS, Suit.SPADES]:
        end_rank_count, singleton_count, middle_count = _own_suit_structure_features(hand, s)
        x[k + 0] = end_rank_count
        x[k + 1] = singleton_count
        x[k + 2] = middle_count
        k += 3

    # board-aware per-suit features [12]
    for s in [Suit.CLUBS, Suit.DIAMONDS, Suit.HEARTS, Suit.SPADES]:
        playable_now_count, one_step_away_count, path_potential = _board_aware_suit_features(
            hand,
            s,
            state.table.bounds[s],
        )
        x[k + 0] = playable_now_count
        x[k + 1] = one_step_away_count
        x[k + 2] = path_potential
        k += 3

    # board control global [4] + per suit [8]
    total_open_slots = 0
    own_open_slots = 0
    per_suit_stats: list[tuple[int, int]] = []

    for s in [Suit.CLUBS, Suit.DIAMONDS, Suit.HEARTS, Suit.SPADES]:
        open_slots_s, own_open_slots_s = _open_slot_stats_for_suit(hand, s, state.table.bounds[s])
        total_open_slots += open_slots_s
        own_open_slots += own_open_slots_s
        per_suit_stats.append((open_slots_s, own_open_slots_s))

    other_open_slots = total_open_slots - own_open_slots
    own_open_slot_share = (own_open_slots / total_open_slots) if total_open_slots > 0 else 0.0

    x[k + 0] = total_open_slots / 8.0
    x[k + 1] = own_open_slots / 8.0
    x[k + 2] = other_open_slots / 8.0
    x[k + 3] = own_open_slot_share
    k += 4

    for open_slots_s, own_open_slots_s in per_suit_stats:
        x[k + 0] = open_slots_s / 2.0
        x[k + 1] = own_open_slots_s / 2.0
        k += 2

    # open7 follow-up depth [4]
    for s in [Suit.CLUBS, Suit.DIAMONDS, Suit.HEARTS, Suit.SPADES]:
        x[k] = _open7_followup_depth(hand, s, state.table.bounds[s])
        k += 1

    assert k == OBS_DIM
    return x