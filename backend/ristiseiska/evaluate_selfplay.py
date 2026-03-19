from __future__ import annotations

import argparse
from collections import defaultdict

import numpy as np
import torch
import torch.nn as nn

from backend.ristiseiska import reset
from backend.ristiseiska import step
from backend.ristiseiska import available_actions
from backend.ristiseiska import observe, OBS_DIM
from backend.ristiseiska.mask import legal_action_mask
from backend.ristiseiska import ACTION_DIM, decode_action


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


@torch.no_grad()
def pick_action(model: nn.Module, state, player: int, device: torch.device, mode: str, temp: float):
    obs = observe(state, player)
    mask = legal_action_mask(state, player)

    x = torch.from_numpy(obs).to(device).unsqueeze(0)  # [1, OBS_DIM]
    logits = model(x).squeeze(0)  # [ACTION_DIM]

    mask_t = torch.from_numpy(mask).to(device)
    neg_inf = torch.tensor(-1e9, device=device, dtype=logits.dtype)
    logits = torch.where(mask_t, logits, neg_inf)

    if mode == "argmax":
        a_id = int(torch.argmax(logits).item())
        return decode_action(a_id)

    logits = logits / float(temp)
    dist = torch.distributions.Categorical(logits=logits)
    a_id = int(dist.sample().item())
    return decode_action(a_id)


def _print_report(
        games_done: int,
        games_total: int,
        model_path: str,
        mode: str,
        temp: float,
        win_counts,
        lose_counts,
        rank_sums,
        starter_wins: int,
        steps_list,
        stats,
        timeouts: int,
        cycles: int,
        timeout_seeds: list[int],
        cont_legal,
        cont_chosen,
):
    if games_done == 0:
        print("No games completed yet.")
        return

    print("=" * 60)
    print(f"Self-play evaluation over {games_done}/{games_total} games")
    print(f"Model: {model_path}")
    print(f"Mode: {mode} (temp={temp})")
    print("=" * 60)

    for i in range(4):
        print(
            f"P{i} | win={win_counts[i]/games_done:.3f} "
            f"lose={lose_counts[i]/games_done:.3f} "
            f"rank_mean={rank_sums[i]/games_done:.3f}"
        )

    print("-" * 60)
    print(f"Starter wins: {starter_wins/games_done:.3f}")
    print(f"Timeouts: {timeouts} ({timeouts/games_done:.3f})")
    print(f"Cycles (approx): {cycles} ({cycles/games_done:.3f})")

    if timeouts:
        # show up to 20 to avoid wall of text
        shown = timeout_seeds[:20]
        more = "" if len(timeout_seeds) <= 20 else f" (+{len(timeout_seeds)-20} more)"
        print(f"Timeout seeds (first {len(shown)}): {shown}{more}")

    if steps_list:
        print(
            f"Avg steps: {float(np.mean(steps_list)):.1f} | "
            f"p50: {float(np.percentile(steps_list, 50)):.1f} | "
            f"p90: {float(np.percentile(steps_list, 90)):.1f}"
        )

    print("-" * 60)
    print("Action stats per player (per-game averages):")
    keys = ["play", "request", "give", "cont", "open_suit"]
    for i in range(4):
        per_game = {k: v / games_done for k, v in stats[i].items()}
        line = ", ".join(f"{k}={per_game.get(k, 0.0):.2f}" for k in keys)
        print(f"P{i}: {line}")

    print("-" * 60)
    print("CONT analysis (per-game averages):")
    for i in range(4):
        legal_pg = cont_legal[i] / games_done
        chosen_pg = cont_chosen[i] / games_done
        rate = (cont_chosen[i] / cont_legal[i]) if cont_legal[i] > 0 else 0.0
        print(f"P{i}: cont_legal={legal_pg:.2f}  cont_chosen={chosen_pg:.2f}  chosen/legal={rate:.3f}")

    print("=" * 60)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", type=str, default="policy_best.pt")
    ap.add_argument("--games", type=int, default=500)
    ap.add_argument("--device", type=str, default="cpu")
    ap.add_argument("--mode", type=str, default="argmax", choices=["argmax", "sample"])
    ap.add_argument("--temp", type=float, default=1.0)
    ap.add_argument("--max-steps", type=int, default=20000)
    ap.add_argument("--progress-every", type=int, default=25)
    ap.add_argument("--seed", type=int, default=10000)
    ap.add_argument("--cycle-check-every", type=int, default=50)
    args = ap.parse_args()

    device = torch.device(args.device)

    model = PolicyNet(OBS_DIM, ACTION_DIM).to(device)
    model.load_state_dict(torch.load(args.model, map_location=device))
    model.eval()

    win_counts = [0, 0, 0, 0]
    lose_counts = [0, 0, 0, 0]
    rank_sums = [0, 0, 0, 0]
    starter_wins = 0

    stats = [defaultdict(int) for _ in range(4)]
    steps_list = []

    # cont analysis
    cont_legal = [0, 0, 0, 0]
    cont_chosen = [0, 0, 0, 0]

    timeouts = 0
    cycles = 0
    timeout_seeds: list[int] = []
    games_done = 0

    try:
        for g in range(args.games):
            seed = args.seed + g
            state = reset(seed=seed)
            steps = 0
            seen = set()
            cycle_hit = False

            while not state.done and steps < args.max_steps:
                steps += 1
                p = state.turn

                actions = available_actions(state, p)
                if not actions:
                    raise RuntimeError("No legal actions")

                before_bounds = dict(state.table.bounds)

                # ---- cont legal analysis (based on mask) ----
                mask = legal_action_mask(state, p)
                # cont actions are indices 52..103
                cont_legal[p] += int(mask[52:104].any())

                a = pick_action(model, state, p, device, mode=args.mode, temp=args.temp)
                if a not in actions:
                    a = actions[0]

                # chosen cont?
                if a.kind == "PLAY" and getattr(a, "cont", False):
                    cont_chosen[p] += 1

                # ---- stats (based on chosen action) ----
                if a.kind == "PLAY":
                    stats[p]["play"] += 1
                    if getattr(a, "cont", False):
                        stats[p]["cont"] += 1
                    if a.card is not None and a.card.rank == 7:
                        if before_bounds[a.card.suit] is None:
                            stats[p]["open_suit"] += 1
                elif a.kind == "REQUEST":
                    stats[p]["request"] += 1
                elif a.kind == "GIVE":
                    stats[p]["give"] += 1

                step(state, a)

                # Approx cycle detection (coarse signature every N steps)
                if args.cycle_check_every > 0 and steps % args.cycle_check_every == 0:
                    sig = (
                        state.turn,
                        state.pending_give_from,
                        state.pending_give_to,
                        tuple(len(h) for h in state.hands),
                        tuple(
                            (s.value, state.table.bounds[s] if state.table.bounds[s] is not None else None)
                            for s in state.table.bounds.keys()
                        ),
                    )
                    if sig in seen:
                        cycle_hit = True
                        break
                    seen.add(sig)

            games_done += 1

            if not state.done:
                timeouts += 1
                timeout_seeds.append(seed)
                if cycle_hit:
                    cycles += 1
                steps_list.append(steps)

                if args.progress_every > 0 and games_done % args.progress_every == 0:
                    print(f"games done: {games_done}/{args.games} (timeouts so far: {timeouts})")
                continue

            # finished normally
            steps_list.append(steps)

            for i in range(4):
                rank = state.placements.index(i) + 1
                rank_sums[i] += rank
                if rank == 1:
                    win_counts[i] += 1
                if rank == 4:
                    lose_counts[i] += 1

            if state.placements[0] == state.starter:
                starter_wins += 1

            if args.progress_every > 0 and games_done % args.progress_every == 0:
                print(f"games done: {games_done}/{args.games} (timeouts so far: {timeouts})")

    except KeyboardInterrupt:
        print("\nInterrupted (Ctrl+C). Printing partial results...\n")

    _print_report(
        games_done=games_done,
        games_total=args.games,
        model_path=args.model,
        mode=args.mode,
        temp=args.temp,
        win_counts=win_counts,
        lose_counts=lose_counts,
        rank_sums=rank_sums,
        starter_wins=starter_wins,
        steps_list=steps_list,
        stats=stats,
        timeouts=timeouts,
        cycles=cycles,
        timeout_seeds=timeout_seeds,
        cont_legal=cont_legal,
        cont_chosen=cont_chosen,
    )


if __name__ == "__main__":
    main()
