from __future__ import annotations

import random
import time

from ristiseiska.state import reset, TableState
from ristiseiska.cards import Suit, RANK_STR
from ristiseiska.moves import available_actions
from ristiseiska.engine import step


SUIT_ORDER = [Suit.CLUBS, Suit.DIAMONDS, Suit.HEARTS, Suit.SPADES]
SUIT_HDR = ["♣", "♦", "♥", "♠"]


def r(rank: int) -> str:
    return RANK_STR.get(rank, str(rank))


def cell(txt: str) -> str:
    return f"[{txt:^3}]"


def board_3x4(table: TableState) -> str:
    """
    3 rows x 4 suits:
      row0: highest up-card (if > 7)
      row1: 7 (if suit started)
      row2: lowest down-card (if down-chain opened; low != 7). NOTE: Ace is rank 14.
    """
    top, mid, bot = [], [], []

    for s in SUIT_ORDER:
        b = table.bounds[s]
        if b is None:
            top.append(cell(""))
            mid.append(cell(""))
            bot.append(cell(""))
            continue

        low, high = b
        mid.append(cell("7"))
        top.append(cell(r(high) if high > 7 else ""))
        bot.append(cell(r(low) if low != 7 else ""))

    header = "    " + " ".join(f" {h}  " for h in SUIT_HDR)
    return "\n".join([header, " ".join(top), " ".join(mid), " ".join(bot)])


def count_table_cards(table: TableState) -> int:
    return sum(len(s) for s in table.played.values())


def _auto_seed() -> int:
    # 32-bit-ish seed from time (good enough for demo randomness)
    return int(time.time_ns() % (2**32))


def main(
        deal_seed: int | None = 42,
        policy_seed: int | None = None,
        max_steps: int = 5000,
        progress_every: int = 100,
) -> None:
    """
    deal_seed controls shuffling/deal determinism.
    policy_seed controls the random agent's choices.
      - If policy_seed is None, we use system randomness (non-deterministic per run).
    """
    if policy_seed is None:
        # non-deterministic behavior per run (system randomness)
        rng = random.Random()
    else:
        rng = random.Random(policy_seed)

    state = reset(seed=deal_seed)

    print("=" * 60)
    print(f"Deal seed:   {deal_seed}")
    print(f"Policy seed: {policy_seed if policy_seed is not None else '(system random)'}")
    print(f"Starter (had 7♣): P{state.starter}")
    print(f"Turn (after forced 7♣): P{state.turn}")
    print("=" * 60)

    print("\n=== INITIAL BOARD ===")
    print(board_3x4(state.table))
    print("Hand sizes:", [len(h) for h in state.hands])
    print("Table cards:", count_table_cards(state.table))
    print("Placements:", state.placements, "Done:", state.done, "Loser:", state.loser)

    t = 0
    while not state.done and t < max_steps:
        t += 1
        p = state.turn

        actions = available_actions(state, p)
        if not actions:
            raise RuntimeError(f"No actions available for current player P{p}")

        action = rng.choice(actions)

        before_from = state.pending_give_from
        before_to = state.pending_give_to

        print("\n" + "-" * 60)
        cont_tag = " (cont)" if getattr(action, "cont", False) else ""
        print(f"STEP {t}: P{p} -> {action.kind} {action.card or ''}{cont_tag}".rstrip())
        print("-" * 60)

        step(state, action)

        if action.kind == "GIVE":
            print(f"GAVE {action.card} from P{before_from} to P{before_to}")

        # Card conservation sanity check
        hand_sizes = [len(h) for h in state.hands]
        table_cards = count_table_cards(state.table)
        total_cards = sum(hand_sizes) + table_cards
        if total_cards != 52:
            raise RuntimeError(f"Card conservation broken: total={total_cards}")

        print(board_3x4(state.table))
        print("Hand sizes:", hand_sizes, "Table cards:", table_cards)
        print("Placements:", state.placements, "Done:", state.done, "Loser:", state.loser)
        print("Next turn:", state.turn)

        if progress_every > 0 and t % progress_every == 0 and not state.done:
            print("\n" + "=" * 60)
            print(f"PROGRESS t={t}")
            print(board_3x4(state.table))
            print("Hand sizes:", hand_sizes, "Table cards:", table_cards)
            print("Placements:", state.placements, "Done:", state.done, "Loser:", state.loser)
            print("=" * 60)

    if state.done:
        print("\n" + "=" * 60)
        print("GAME OVER")
        print("Ranking (winner -> loser):", state.placements)
        print("Loser:", state.loser)
        print("Steps:", t)
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print(f"STOPPED after max_steps={max_steps} (game not finished)")
        print("Hand sizes:", [len(h) for h in state.hands], "Table cards:", count_table_cards(state.table))
        print("Placements:", state.placements, "Done:", state.done, "Loser:", state.loser)
        print("=" * 60)


if __name__ == "__main__":
    # Examples:
    # 1) Same deal every time, different behavior each run:
    #    main(deal_seed=42, policy_seed=None)
    #
    # 2) Same deal, deterministic behavior:
    #    main(deal_seed=42, policy_seed=123)
    #
    # 3) Everything random per run:
    #    main(deal_seed=None, policy_seed=None)
    main(deal_seed=42, policy_seed=None)
