from __future__ import annotations

import argparse
import random
from collections import defaultdict
from statistics import mean
from typing import Dict, List, Tuple

import numpy as np
import torch
import torch.nn as nn

from backend.ristiseiska import reset, GameState
from backend.ristiseiska import step
from backend.ristiseiska import available_actions, Action
from backend.ristiseiska import observe, OBS_DIM, _suit_deadness
from backend.ristiseiska.mask import legal_action_mask
from backend.ristiseiska import ACTION_DIM, decode_action
from backend.ristiseiska import Suit
from backend.ristiseiska import below_from_7, above_from_7


class PolicyNet(nn.Module):
    def __init__(self, in_dim: int, out_dim: int):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(in_dim, 256),
            nn.ReLU(),
            nn.Linear(256, 256),
            nn.ReLU(),
            nn.Linear(256, out_dim),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


def pick_action_heuristic(actions: List[Action], rng: random.Random) -> Action:
    plays = [a for a in actions if a.kind == "PLAY" and not getattr(a, "cont", False)]
    if plays:
        return rng.choice(plays)

    plays2 = [a for a in actions if a.kind == "PLAY"]
    if plays2:
        return rng.choice(plays2)

    gives = [a for a in actions if a.kind == "GIVE"]
    if gives:
        return rng.choice(gives)

    return actions[0]


def load_model(path: str, device: torch.device) -> PolicyNet:
    model = PolicyNet(OBS_DIM, ACTION_DIM).to(device)
    sd = torch.load(path, map_location=device)
    model.load_state_dict(sd)
    model.eval()
    return model


def state_signature(state: GameState) -> Tuple:
    """
    Approximate cycle detection signature.
    Includes turn, pending give info, table bounds, and sorted hands.
    """
    table_sig = tuple(
        (int(s), state.table.bounds[s])
        for s in sorted(state.table.bounds.keys(), key=int)
    )

    hands_sig = tuple(
        tuple((int(c.suit), c.rank) for c in hand)
        for hand in state.hands
    )

    return (
        state.turn,
        state.pending_give_from,
        state.pending_give_to,
        table_sig,
        hands_sig,
        tuple(state.placements),
        state.done,
        state.loser,
    )


def _needed_ranks_from_bounds(bounds: tuple[int, int] | None) -> tuple[int, ...]:
    """
    Same logic as environment:
      - None -> only 7
      - (7,7) -> only 6
      - (6,7) -> only 8
      - after that -> down/up if available
    """
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


def board_control_stats(state: GameState, player: int) -> tuple[int, int, int, float]:
    """
    Compute board-control stats from the player's perspective:
      - total_open_slots
      - own_open_slots
      - other_open_slots
      - own_open_slot_share
    Uses the same slot logic as the environment.
    """
    hand = state.hands[player]
    total_open_slots = 0
    own_open_slots = 0

    for s in [Suit.CLUBS, Suit.DIAMONDS, Suit.HEARTS, Suit.SPADES]:
        needed = _needed_ranks_from_bounds(state.table.bounds[s])
        total_open_slots += len(needed)

        own_ranks = {c.rank for c in hand if c.suit == s}
        own_open_slots += sum(1 for r in needed if r in own_ranks)

    other_open_slots = total_open_slots - own_open_slots
    own_open_slot_share = (own_open_slots / total_open_slots) if total_open_slots > 0 else 0.0

    return total_open_slots, own_open_slots, other_open_slots, own_open_slot_share


def choose_model_action(
        model: PolicyNet,
        state: GameState,
        player: int,
        device: torch.device,
        mode: str,
        temperature: float,
        rng: random.Random,
) -> tuple[Action, bool]:
    """
    Returns:
      (action, used_fallback)
    """
    actions = available_actions(state, player)
    if not actions:
        raise RuntimeError(f"No legal actions for player {player}")

    obs = observe(state, player)
    mask = legal_action_mask(state, player)

    x = torch.from_numpy(obs).to(device).unsqueeze(0)
    logits = model(x).squeeze(0)

    mask_t = torch.from_numpy(mask).to(device)
    neg_inf = torch.tensor(-1e9, device=device, dtype=logits.dtype)
    logits_masked = torch.where(mask_t, logits, neg_inf)

    if mode == "argmax":
        a_id = int(torch.argmax(logits_masked).item())
    elif mode == "sample":
        temp = max(temperature, 1e-6)
        dist = torch.distributions.Categorical(logits=logits_masked / temp)
        a_id = int(dist.sample().item())
    else:
        raise ValueError(f"Unknown mode: {mode}")

    a = decode_action(a_id)
    used_fallback = False

    if a not in actions:
        a = pick_action_heuristic(actions, rng)
        used_fallback = True

    return a, used_fallback


def give_quality_flags(state: GameState, player: int, action: Action) -> Dict[str, int]:
    """
    Analyze GIVE card quality using the hand BEFORE the card is removed.
    """
    result = {"singleton": 0, "end_rank": 0, "middle": 0}

    if action.kind != "GIVE" or action.card is None:
        return result

    c = action.card
    same_suit = [x for x in state.hands[player] if x.suit == c.suit]
    suit_ranks = {x.rank for x in same_suit}

    if len(same_suit) == 1:
        result["singleton"] = 1

    if c.rank in (13, 14):
        result["end_rank"] = 1

    if (c.rank - 1 in suit_ranks) and (c.rank + 1 in suit_ranks):
        result["middle"] = 1

    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model_a", type=str, required=True)
    ap.add_argument("--model_b", type=str, required=True)
    ap.add_argument("--a_seat", type=int, default=0, choices=[0, 1, 2, 3])
    ap.add_argument("--games", type=int, default=2000)
    ap.add_argument("--mode", type=str, default="argmax", choices=["argmax", "sample"])
    ap.add_argument("--temp", type=float, default=1.0)
    ap.add_argument("--device", type=str, default="cpu")
    ap.add_argument("--deal_seed", type=int, default=10000)
    ap.add_argument("--opp_seed", type=int, default=123)
    ap.add_argument("--max_steps", type=int, default=20000)
    args = ap.parse_args()

    device = torch.device(args.device)
    rng = random.Random(args.opp_seed)

    model_a = load_model(args.model_a, device)
    model_b = load_model(args.model_b, device)

    ranks_by_player: Dict[int, List[int]] = {p: [] for p in range(4)}
    winner_count = {p: 0 for p in range(4)}
    loser_count = {p: 0 for p in range(4)}

    action_stats = {p: defaultdict(int) for p in range(4)}
    cont_legal_stats = {p: 0 for p in range(4)}
    cont_chosen_stats = {p: 0 for p in range(4)}

    give_quality = {p: defaultdict(int) for p in range(4)}
    give_totals = {p: 0 for p in range(4)}
    give_deadness = {p: [] for p in range(4)}

    board_control_acc = {p: defaultdict(float) for p in range(4)}
    board_control_count = {p: 0 for p in range(4)}

    fallback_count = {p: 0 for p in range(4)}

    steps_list: List[int] = []
    starter_wins = 0
    timeout_count = 0
    cycle_count = 0

    for g in range(args.games):
        state = reset(seed=args.deal_seed + g)
        starter = state.starter
        seen = set()
        steps = 0

        while not state.done and steps < args.max_steps:
            sig = state_signature(state)
            if sig in seen:
                cycle_count += 1
                break
            seen.add(sig)

            steps += 1
            p = state.turn
            actions = available_actions(state, p)

            if not actions:
                raise RuntimeError(f"No legal actions for player {p}")

            # Continuation analysis: use ONLY available_actions + chosen action
            legal_cont_actions = [
                x for x in actions
                if x.kind == "PLAY" and getattr(x, "cont", False)
            ]
            if legal_cont_actions:
                cont_legal_stats[p] += 1

            # Board-control stats at decision time
            total_open_slots, own_open_slots, other_open_slots, own_open_slot_share = board_control_stats(state, p)
            board_control_acc[p]["total_open_slots"] += total_open_slots
            board_control_acc[p]["own_open_slots"] += own_open_slots
            board_control_acc[p]["other_open_slots"] += other_open_slots
            board_control_acc[p]["own_open_slot_share"] += own_open_slot_share
            board_control_count[p] += 1

            # Choose action
            if p == args.a_seat:
                a, used_fallback = choose_model_action(
                    model=model_a,
                    state=state,
                    player=p,
                    device=device,
                    mode=args.mode,
                    temperature=args.temp,
                    rng=rng,
                )
            else:
                a, used_fallback = choose_model_action(
                    model=model_b,
                    state=state,
                    player=p,
                    device=device,
                    mode=args.mode,
                    temperature=args.temp,
                    rng=rng,
                )

            if used_fallback:
                fallback_count[p] += 1

            # Action stats
            if a.kind == "PLAY":
                action_stats[p]["play"] += 1
                if getattr(a, "cont", False):
                    action_stats[p]["cont"] += 1
                    cont_chosen_stats[p] += 1

                if a.card is not None and state.table.bounds[a.card.suit] is None:
                    action_stats[p]["open_suit"] += 1

            elif a.kind == "REQUEST":
                action_stats[p]["request"] += 1

            elif a.kind == "GIVE":
                action_stats[p]["give"] += 1
                give_totals[p] += 1

                q = give_quality_flags(state, p, a)
                for k, v in q.items():
                    give_quality[p][k] += v

                if a.card is not None:
                    bounds = state.table.bounds[a.card.suit]
                    dead = _suit_deadness(a.card.rank, bounds)
                    give_deadness[p].append(dead)

            step(state, a)

        if not state.done:
            timeout_count += 1
            unresolved = [p for p in range(4) if p not in state.placements]
            unresolved_sorted = sorted(unresolved, key=lambda x: len(state.hands[x]))
            final_placements = list(state.placements) + unresolved_sorted
        else:
            final_placements = list(state.placements)

        for p in range(4):
            rank = final_placements.index(p) + 1
            ranks_by_player[p].append(rank)
            if rank == 1:
                winner_count[p] += 1
            if rank == 4:
                loser_count[p] += 1

        if final_placements[0] == starter:
            starter_wins += 1

        steps_list.append(steps)

        if (g + 1) % 500 == 0 or (g + 1) == args.games:
            print(f"games done: {g + 1}/{args.games} (timeouts so far: {timeout_count})")

    print("=" * 60)
    print(f"Evaluation over {args.games}/{args.games} games")
    print(f"Models: A={args.model_a} (seat {args.a_seat}) vs B={args.model_b}")
    print(f"Mode: {args.mode} (temp={args.temp})")
    print("=" * 60)

    for p in range(4):
        win = winner_count[p] / args.games
        lose = loser_count[p] / args.games
        rank_mean = float(np.mean(ranks_by_player[p]))
        print(f"P{p} | win={win:.3f} lose={lose:.3f} rank_mean={rank_mean:.3f}")

    print("-" * 60)
    print(f"Starter wins: {starter_wins / args.games:.3f}")
    print(f"Timeouts: {timeout_count} ({timeout_count / args.games:.3f})")
    print(f"Cycles (approx): {cycle_count} ({cycle_count / args.games:.3f})")
    print(
        f"Avg steps: {mean(steps_list):.1f} | "
        f"p50: {np.percentile(steps_list, 50):.1f} | "
        f"p90: {np.percentile(steps_list, 90):.1f}"
    )

    print("-" * 60)
    print("Action stats per player (per-game averages):")
    for p in range(4):
        play = action_stats[p]["play"] / args.games
        request = action_stats[p]["request"] / args.games
        give = action_stats[p]["give"] / args.games
        cont = action_stats[p]["cont"] / args.games
        open_suit = action_stats[p]["open_suit"] / args.games
        print(
            f"P{p}: play={play:.2f}, request={request:.2f}, "
            f"give={give:.2f}, cont={cont:.2f}, open_suit={open_suit:.2f}"
        )

    print("-" * 60)
    print("CONT analysis (per-game averages):")
    for p in range(4):
        cont_legal = cont_legal_stats[p] / args.games
        cont_chosen = cont_chosen_stats[p] / args.games
        ratio = (cont_chosen_stats[p] / cont_legal_stats[p]) if cont_legal_stats[p] > 0 else 0.0
        print(
            f"P{p}: cont_legal={cont_legal:.2f}  "
            f"cont_chosen={cont_chosen:.2f}  chosen/legal={ratio:.3f}"
        )

    print("-" * 60)
    print("GIVE quality (fractions of GIVE actions):")
    for p in range(4):
        total = give_totals[p]
        if total == 0:
            print(f"P{p}: no give actions")
            continue

        singleton = give_quality[p]["singleton"] / total
        end_rank = give_quality[p]["end_rank"] / total
        middle = give_quality[p]["middle"] / total

        print(
            f"P{p}: singleton={singleton:.3f}  "
            f"end_rank={end_rank:.3f}  middle={middle:.3f}"
        )

    print("-" * 60)
    print("GIVE deadness (board distance before card given):")
    for p in range(4):
        data = give_deadness[p]
        if not data:
            print(f"P{p}: no give actions")
            continue

        avg_d = float(np.mean(data))
        p50 = float(np.percentile(data, 50))
        p90 = float(np.percentile(data, 90))

        print(f"P{p}: avg={avg_d:.2f}  p50={p50:.2f}  p90={p90:.2f}")

    print("-" * 60)
    print("Board control (averages at decision time):")
    for p in range(4):
        cnt = board_control_count[p]
        if cnt == 0:
            print(f"P{p}: no decisions")
            continue

        total_open = board_control_acc[p]["total_open_slots"] / cnt
        own_open = board_control_acc[p]["own_open_slots"] / cnt
        other_open = board_control_acc[p]["other_open_slots"] / cnt
        share = board_control_acc[p]["own_open_slot_share"] / cnt

        print(
            f"P{p}: total_open_slots={total_open:.2f}  "
            f"own_open_slots={own_open:.2f}  "
            f"other_open_slots={other_open:.2f}  "
            f"own_open_slot_share={share:.3f}"
        )

    print("-" * 60)
    print("Fallbacks (model decoded illegal action -> heuristic fallback):")
    for p in range(4):
        print(f"P{p}: {fallback_count[p]}")

    print("=" * 60)


if __name__ == "__main__":
    main()