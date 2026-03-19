from __future__ import annotations

import argparse
import random
from collections import Counter

import numpy as np
import torch
import torch.nn as nn

from ristiseiska.state import reset
from ristiseiska.engine import step
from ristiseiska.moves import available_actions, Action
from ristiseiska.obs import observe, OBS_DIM
from ristiseiska.mask import legal_action_mask
from ristiseiska.actions import ACTION_DIM, decode_action


# Same network architecture as in train_bc.py
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
    # Prefer PLAY non-cont; else any PLAY; else GIVE random; else REQUEST
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


@torch.no_grad()
def pick_action_model(model: nn.Module, state, player: int, device: torch.device) -> Action:
    obs = observe(state, player)  # [OBS_DIM]
    mask = legal_action_mask(state, player)  # [ACTION_DIM] bool

    x = torch.from_numpy(obs).to(device).unsqueeze(0)  # [1, OBS_DIM]
    logits = model(x).squeeze(0)  # [ACTION_DIM]

    # Mask illegal actions
    mask_t = torch.from_numpy(mask).to(device)
    neg_inf = torch.tensor(-1e9, device=device, dtype=logits.dtype)
    logits_masked = torch.where(mask_t, logits, neg_inf)

    a_id = int(torch.argmax(logits_masked).item())
    return decode_action(a_id)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", type=str, default="policy_bc.pt")
    ap.add_argument("--games", type=int, default=200)
    ap.add_argument("--deal-seed", type=int, default=1000)
    ap.add_argument("--opp-seed", type=int, default=123)
    ap.add_argument("--max-steps", type=int, default=20000)
    ap.add_argument("--device", type=str, default="cpu")
    args = ap.parse_args()

    device = torch.device(args.device)

    model = PolicyNet(OBS_DIM, ACTION_DIM).to(device)
    sd = torch.load(args.model, map_location=device)
    model.load_state_dict(sd)
    model.eval()

    rng = random.Random(args.opp_seed)

    loser_count = 0
    winner_count = 0
    rank_counts = Counter()
    steps_list = []

    for g in range(args.games):
        state = reset(seed=args.deal_seed + g)
        steps = 0

        while not state.done and steps < args.max_steps:
            steps += 1
            p = state.turn
            actions = available_actions(state, p)
            if not actions:
                raise RuntimeError(f"No actions for player {p}")

            if p == 0:
                a = pick_action_model(model, state, p, device)
                # Safety: if model somehow picks illegal (shouldn't due to mask), fall back.
                if a not in actions:
                    a = pick_action_heuristic(actions, rng)
            else:
                a = pick_action_heuristic(actions, rng)

            step(state, a)

        if not state.done:
            raise RuntimeError(f"Game {g} did not finish in max_steps={args.max_steps}")

        steps_list.append(steps)

        # placements: winner -> loser
        # rank for player 0 is index+1 in placements
        rank = state.placements.index(0) + 1
        rank_counts[rank] += 1

        if state.loser == 0:
            loser_count += 1
        if state.placements[0] == 0:
            winner_count += 1

    games = args.games
    avg_steps = float(np.mean(steps_list))
    p50_steps = float(np.percentile(steps_list, 50))
    p90_steps = float(np.percentile(steps_list, 90))

    print("=" * 60)
    print(f"Games: {games}")
    print(f"Model: {args.model}")
    print(f"Avg steps: {avg_steps:.1f} | p50: {p50_steps:.1f} | p90: {p90_steps:.1f}")
    print(f"Winner rate (P0 rank 1): {winner_count/games:.3f} ({winner_count}/{games})")
    print(f"Loser  rate (P0 rank 4): {loser_count/games:.3f} ({loser_count}/{games})")
    print("Rank distribution for P0:")
    for r in [1, 2, 3, 4]:
        print(f"  rank {r}: {rank_counts[r]} ({rank_counts[r]/games:.3f})")
    print("=" * 60)


if __name__ == "__main__":
    main()
