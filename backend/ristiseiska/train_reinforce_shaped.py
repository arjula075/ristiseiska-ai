from __future__ import annotations

import argparse
import random
from collections import deque
from functools import lru_cache

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim

from backend.ristiseiska import reset
from backend.ristiseiska import step
from backend.ristiseiska import available_actions, Action
from backend.ristiseiska import observe, OBS_DIM
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


def pick_action_heuristic(actions: list[Action], rng: random.Random) -> Action:
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


def terminal_rank_reward(rank: int) -> float:
    if rank == 1:
        return 1.0
    if rank == 2:
        return 0.2
    if rank == 3:
        return -0.2
    return -0.6


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

    raise ValueError(f"Rank {rank} is not legal for bounds {bounds}")


def _suit_path_potential(hand, suit: Suit, bounds: tuple[int, int] | None) -> int:
    """
    Max number of own cards in this suit that can be drained in sequence
    from current bounds, assuming favorable turn opportunities.
    """
    suit_ranks = tuple(sorted(c.rank for c in hand if c.suit == suit))

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

    return best_chain(bounds, suit_ranks)


def _total_path_potential_for_player(state, player: int) -> int:
    total = 0
    for s in [Suit.CLUBS, Suit.DIAMONDS, Suit.HEARTS, Suit.SPADES]:
        total += _suit_path_potential(state.hands[player], s, state.table.bounds[s])
    return total


@torch.no_grad()
def evaluate(
        model: nn.Module,
        games: int,
        deal_seed: int,
        opp_seed: int,
        device: torch.device,
        max_steps: int,
) -> dict:
    rng = random.Random(opp_seed)

    ranks = []
    steps_list = []
    winner = 0
    loser = 0

    model.eval()

    for g in range(games):
        state = reset(seed=deal_seed + g)
        steps = 0

        while not state.done and steps < max_steps:
            steps += 1
            p = state.turn
            actions = available_actions(state, p)
            if not actions:
                raise RuntimeError(f"No actions for player {p}")

            if p == 0:
                obs = observe(state, 0)
                mask = legal_action_mask(state, 0)

                x = torch.from_numpy(obs).to(device).unsqueeze(0)
                logits = model(x).squeeze(0)

                mask_t = torch.from_numpy(mask).to(device)
                neg_inf = torch.tensor(-1e9, device=device, dtype=logits.dtype)
                logits_masked = torch.where(mask_t, logits, neg_inf)

                a_id = int(torch.argmax(logits_masked).item())
                a = decode_action(a_id)
                if a not in actions:
                    a = pick_action_heuristic(actions, rng)
            else:
                a = pick_action_heuristic(actions, rng)

            step(state, a)

        if not state.done:
            rank = 4
        else:
            rank = state.placements.index(0) + 1

        steps_list.append(steps)
        ranks.append(rank)
        if rank == 1:
            winner += 1
        if rank == 4:
            loser += 1

    return {
        "winner_rate": winner / games,
        "loser_rate": loser / games,
        "rank_mean": float(np.mean(ranks)),
        "steps_mean": float(np.mean(steps_list)),
        "steps_p90": float(np.percentile(steps_list, 90)),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--episodes", type=int, default=3000)
    ap.add_argument("--max-steps", type=int, default=20000)
    ap.add_argument("--deal-seed", type=int, default=1000)
    ap.add_argument("--opp-seed", type=int, default=123)

    ap.add_argument("--lr", type=float, default=3e-4)
    ap.add_argument("--baseline-alpha", type=float, default=0.05)

    # shaping weights
    ap.add_argument("--w-hand-delta", type=float, default=0.02)   # reward per net card removed from P0 hand
    ap.add_argument("--w-step", type=float, default=0.001)        # penalty per env step
    ap.add_argument("--w-cont", type=float, default=0.005)        # small bonus when P0 chooses cont=True
    ap.add_argument("--w-path-delta", type=float, default=0.01)   # reward for preserving/growing own path potential
    ap.add_argument("--w-end-play", type=float, default=0.003)    # small bonus for playing A/K

    ap.add_argument("--eval-every", type=int, default=200)
    ap.add_argument("--eval-games", type=int, default=300)
    ap.add_argument(
        "--best-metric",
        type=str,
        default="rank_mean",
        choices=["rank_mean", "loser_rate", "winner_rate"],
    )

    ap.add_argument("--device", type=str, default="cpu")
    ap.add_argument("--init", type=str, default="", help="Optional init weights (e.g. policy_bc.pt)")
    ap.add_argument("--out", type=str, default="policy_rl_shaped.pt")
    ap.add_argument("--best-out", type=str, default="policy_best_shaped.pt")
    args = ap.parse_args()

    device = torch.device(args.device)

    model = PolicyNet(OBS_DIM, ACTION_DIM).to(device)
    if args.init:
        sd = torch.load(args.init, map_location=device)
        model.load_state_dict(sd)
        print(f"Loaded init weights from {args.init}")

    opt = optim.Adam(model.parameters(), lr=args.lr)
    rng = random.Random(args.opp_seed)

    baseline = 0.0
    recent_returns = deque(maxlen=200)

    best_score = None

    for ep in range(1, args.episodes + 1):
        state = reset(seed=args.deal_seed + ep)

        logprobs = []
        entropies = []

        shaped_R = 0.0
        steps = 0

        while not state.done and steps < args.max_steps:
            steps += 1
            p = state.turn
            actions = available_actions(state, p)
            if not actions:
                raise RuntimeError(f"No actions for player {p}")

            before_len0 = len(state.hands[0])
            before_path0 = _total_path_potential_for_player(state, 0)

            if p == 0:
                obs = observe(state, 0)
                mask = legal_action_mask(state, 0)

                x = torch.from_numpy(obs).to(device).unsqueeze(0)
                logits = model(x).squeeze(0)

                mask_t = torch.from_numpy(mask).to(device)
                neg_inf = torch.tensor(-1e9, device=device, dtype=logits.dtype)
                logits_masked = torch.where(mask_t, logits, neg_inf)

                dist = torch.distributions.Categorical(logits=logits_masked)
                a_id = dist.sample()
                logp = dist.log_prob(a_id)
                entropy = dist.entropy()

                a = decode_action(int(a_id.item()))
                if a not in actions:
                    a = pick_action_heuristic(actions, rng)
                    step(state, a)
                    continue

                logprobs.append(logp)
                entropies.append(entropy)

                # Decision-type shaping only for genuine choices
                if a.kind == "PLAY" and getattr(a, "cont", False):
                    shaped_R += args.w_cont

                if a.kind == "PLAY" and a.card is not None and a.card.rank in (13, 14):
                    shaped_R += args.w_end_play

                step(state, a)
            else:
                a = pick_action_heuristic(actions, rng)
                step(state, a)

            after_len0 = len(state.hands[0])
            after_path0 = _total_path_potential_for_player(state, 0)

            hand_delta = before_len0 - after_len0
            path_delta = after_path0 - before_path0

            shaped_R += args.w_hand_delta * float(hand_delta)
            shaped_R += args.w_path_delta * float(path_delta)

            # discourage stalling
            shaped_R -= args.w_step

        if not state.done:
            rank = 4
        else:
            rank = state.placements.index(0) + 1

        term_R = terminal_rank_reward(rank)
        R_total = term_R + shaped_R
        recent_returns.append(R_total)

        baseline = (1 - args.baseline_alpha) * baseline + args.baseline_alpha * R_total
        adv = R_total - baseline

        if logprobs:
            loss = -(adv * torch.stack(logprobs).sum())
            ent_bonus = 0.001 * torch.stack(entropies).sum()
            total = loss - ent_bonus

            opt.zero_grad()
            total.backward()
            nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step()

        if ep % 50 == 0:
            mean_r = float(np.mean(recent_returns)) if recent_returns else 0.0
            print(
                f"ep={ep:5d} rank={rank} term={term_R:+.2f} "
                f"shaped={shaped_R:+.2f} total={R_total:+.2f} "
                f"base={baseline:+.2f} mean200={mean_r:+.2f} steps={steps}"
            )

        if args.eval_every > 0 and ep % args.eval_every == 0:
            stats = evaluate(
                model=model,
                games=args.eval_games,
                deal_seed=30000 + ep * 10,
                opp_seed=args.opp_seed,
                device=device,
                max_steps=args.max_steps,
            )

            metric = stats[args.best_metric]
            improved = False
            if best_score is None:
                improved = True
            elif args.best_metric in ["rank_mean", "loser_rate"]:
                improved = metric < best_score
            else:
                improved = metric > best_score

            print("-" * 60)
            print(f"EVAL @ ep {ep} | {stats} | best_metric={args.best_metric}={metric:.3f}")
            if improved:
                best_score = metric
                torch.save(model.state_dict(), args.best_out)
                print(f"NEW BEST -> saved {args.best_out} (score={best_score:.3f})")
            print("-" * 60)

    torch.save(model.state_dict(), args.out)
    print("Saved final:", args.out)


if __name__ == "__main__":
    main()