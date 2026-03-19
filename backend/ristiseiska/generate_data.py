from __future__ import annotations

import argparse
import random
from collections import Counter

import numpy as np

from ristiseiska.state import reset
from ristiseiska.engine import step
from ristiseiska.moves import available_actions, Action
from ristiseiska.actions import encode_action
from ristiseiska.obs import observe
from ristiseiska.mask import legal_action_mask


# ------------------------------------------------------------
# Action helpers
# ------------------------------------------------------------

def is_cont_play(a: Action) -> bool:
    return a.kind == "PLAY" and bool(getattr(a, "cont", False))


def is_end_rank_action(a: Action) -> bool:
    card = getattr(a, "card", None)
    if card is None:
        return False
    return getattr(card, "rank", None) in (1, 13, 14)  # A, K, maybe 1 if ace encoded as 1


def action_kind_counts(actions: list[Action]) -> dict[str, int]:
    c = Counter(a.kind for a in actions)
    return {
        "PLAY": c.get("PLAY", 0),
        "GIVE": c.get("GIVE", 0),
        "REQUEST": c.get("REQUEST", 0),
    }


def classify_state(actions: list[Action]) -> dict[str, int | bool]:
    counts = action_kind_counts(actions)
    num_actions = len(actions)
    num_play = counts["PLAY"]
    num_give = counts["GIVE"]
    num_request = counts["REQUEST"]
    cont_legal = any(is_cont_play(a) for a in actions)

    # "Forced" means no actual choice at action level.
    is_forced = (num_actions == 1)

    # "Interesting" means the model has a meaningful choice to learn.
    is_interesting = (
            num_actions > 1
            or num_play > 1
            or num_give > 1
            or cont_legal
    )

    return {
        "num_actions": num_actions,
        "num_play": num_play,
        "num_give": num_give,
        "num_request": num_request,
        "cont_legal": cont_legal,
        "is_forced": is_forced,
        "is_interesting": is_interesting,
    }


# ------------------------------------------------------------
# Lightweight policy mix for within-rule choices
# ------------------------------------------------------------

def choose_action_style(
        actions: list[Action],
        rng: random.Random,
        style: str,
) -> Action:
    """
    Important:
    The house rules decide the action class at a high level
    (must play / must request / must give).
    The remaining choice is usually WHICH legal play or WHICH legal give.

    This chooser only diversifies those within-class decisions.
    """

    if len(actions) == 1:
        return actions[0]

    plays = [a for a in actions if a.kind == "PLAY"]
    gives = [a for a in actions if a.kind == "GIVE"]
    requests = [a for a in actions if a.kind == "REQUEST"]

    cont_plays = [a for a in plays if is_cont_play(a)]
    noncont_plays = [a for a in plays if not is_cont_play(a)]

    end_rank_plays = [a for a in plays if is_end_rank_action(a)]
    non_end_rank_plays = [a for a in plays if not is_end_rank_action(a)]

    end_rank_gives = [a for a in gives if is_end_rank_action(a)]
    non_end_rank_gives = [a for a in gives if not is_end_rank_action(a)]

    # If rules force PLAY, all legal actions should be PLAYs.
    if plays:
        if style == "cont_pref":
            if cont_plays:
                return rng.choice(cont_plays)
            return rng.choice(plays)

        if style == "end_pref":
            if end_rank_plays:
                return rng.choice(end_rank_plays)
            return rng.choice(plays)

        if style == "noncont_pref":
            if noncont_plays:
                return rng.choice(noncont_plays)
            return rng.choice(plays)

        if style == "nonend_pref":
            if non_end_rank_plays:
                return rng.choice(non_end_rank_plays)
            return rng.choice(plays)

        return rng.choice(plays)

    # If rules force GIVE, all legal actions should be GIVEs.
    if gives:
        if style == "end_pref":
            if end_rank_gives:
                return rng.choice(end_rank_gives)
            return rng.choice(gives)

        if style == "nonend_pref":
            if non_end_rank_gives:
                return rng.choice(non_end_rank_gives)
            return rng.choice(gives)

        return rng.choice(gives)

    # Usually request is forced, but keep fallback safe.
    if requests:
        return rng.choice(requests)

    return actions[0]


def pick_style(rng: random.Random) -> str:
    """
    Per-game style assignment.
    The point is not to claim these are "optimal" teachers,
    but to avoid teaching only one exact tie-break policy.
    """
    styles = [
        "uniform",
        "cont_pref",
        "end_pref",
        "noncont_pref",
        "nonend_pref",
    ]
    weights = [0.35, 0.20, 0.15, 0.15, 0.15]
    return rng.choices(styles, weights=weights, k=1)[0]


# ------------------------------------------------------------
# Dataset append
# ------------------------------------------------------------

def append_sample(
        obs_list: list[np.ndarray],
        mask_list: list[np.ndarray],
        act_list: list[int],
        meta_forced: list[np.ndarray],
        meta_interesting: list[np.ndarray],
        meta_num_actions: list[np.ndarray],
        meta_num_play: list[np.ndarray],
        meta_num_give: list[np.ndarray],
        meta_cont_legal: list[np.ndarray],
        obs: np.ndarray,
        mask: np.ndarray,
        aid: int,
        info: dict[str, int | bool],
        repeat: int,
) -> None:
    for _ in range(repeat):
        obs_list.append(obs.copy())
        mask_list.append(mask.copy())
        act_list.append(aid)

        meta_forced.append(np.array(bool(info["is_forced"]), dtype=np.bool_))
        meta_interesting.append(np.array(bool(info["is_interesting"]), dtype=np.bool_))
        meta_num_actions.append(np.array(int(info["num_actions"]), dtype=np.int16))
        meta_num_play.append(np.array(int(info["num_play"]), dtype=np.int16))
        meta_num_give.append(np.array(int(info["num_give"]), dtype=np.int16))
        meta_cont_legal.append(np.array(bool(info["cont_legal"]), dtype=np.bool_))


# ------------------------------------------------------------
# Main
# ------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser()

    ap.add_argument("--out", type=str, default="dataset.npz")
    ap.add_argument("--samples", type=int, default=50000)

    ap.add_argument("--deal-seed", type=int, default=42)
    ap.add_argument("--policy-seed", type=int, default=123)
    ap.add_argument("--max-steps-per-game", type=int, default=10000)

    # New controls
    ap.add_argument(
        "--keep-forced-prob",
        type=float,
        default=0.25,
        help="Probability of keeping a fully forced state (default 0.25).",
    )
    ap.add_argument(
        "--interesting-multiplier",
        type=int,
        default=2,
        help="How many times to store interesting states (default 2).",
    )
    ap.add_argument(
        "--seat0-only",
        action="store_true",
        help="Only collect samples from player 0's turns.",
    )
    ap.add_argument(
        "--print-every",
        type=int,
        default=10,
        help="Progress print interval in games.",
    )

    args = ap.parse_args()

    if not (0.0 <= args.keep_forced_prob <= 1.0):
        raise ValueError("--keep-forced-prob must be in [0, 1]")

    if args.interesting_multiplier < 1:
        raise ValueError("--interesting-multiplier must be >= 1")

    rng = random.Random(args.policy_seed)

    obs_list: list[np.ndarray] = []
    mask_list: list[np.ndarray] = []
    act_list: list[int] = []

    # extra metadata; train_bc.py ignores these, which is fine
    meta_forced: list[np.ndarray] = []
    meta_interesting: list[np.ndarray] = []
    meta_num_actions: list[np.ndarray] = []
    meta_num_play: list[np.ndarray] = []
    meta_num_give: list[np.ndarray] = []
    meta_cont_legal: list[np.ndarray] = []

    kept_forced = 0
    skipped_forced = 0
    kept_interesting = 0

    n = 0
    game_i = 0

    while n < args.samples:
        deal_seed = args.deal_seed + game_i
        state = reset(seed=deal_seed)
        game_i += 1

        # assign one style per player for this game
        styles = [pick_style(rng) for _ in range(4)]

        steps = 0

        while (not state.done) and steps < args.max_steps_per_game and n < args.samples:
            steps += 1
            p = state.turn

            actions = available_actions(state, p)
            if not actions:
                raise RuntimeError(f"No actions for player {p}")

            info = classify_state(actions)

            # Action is chosen for the environment regardless of whether we keep the sample.
            a = choose_action_style(actions, rng, styles[p])

            # Collect only selected seats if requested
            should_consider_for_dataset = (not args.seat0_only) or (p == 0)

            if should_consider_for_dataset:
                keep = True
                repeat = 1

                if bool(info["is_forced"]):
                    if rng.random() <= args.keep_forced_prob:
                        kept_forced += 1
                    else:
                        skipped_forced += 1
                        keep = False
                else:
                    if bool(info["is_interesting"]):
                        kept_interesting += 1
                        repeat = args.interesting_multiplier

                if keep:
                    obs = observe(state, p)
                    mask = legal_action_mask(state, p)
                    aid = encode_action(a)

                    # avoid overshooting too much
                    remaining = args.samples - n
                    if repeat > remaining:
                        repeat = remaining

                    append_sample(
                        obs_list=obs_list,
                        mask_list=mask_list,
                        act_list=act_list,
                        meta_forced=meta_forced,
                        meta_interesting=meta_interesting,
                        meta_num_actions=meta_num_actions,
                        meta_num_play=meta_num_play,
                        meta_num_give=meta_num_give,
                        meta_cont_legal=meta_cont_legal,
                        obs=obs,
                        mask=mask,
                        aid=aid,
                        info=info,
                        repeat=repeat,
                    )
                    n += repeat

            step(state, a)

        if args.print_every > 0 and game_i % args.print_every == 0:
            print(
                f"games={game_i} samples={n} "
                f"kept_forced={kept_forced} skipped_forced={skipped_forced} "
                f"kept_interesting={kept_interesting}"
            )

    obs_arr = np.stack(obs_list).astype(np.float32)
    mask_arr = np.stack(mask_list).astype(np.bool_)
    act_arr = np.array(act_list, dtype=np.int64)

    forced_arr = np.array(meta_forced, dtype=np.bool_)
    interesting_arr = np.array(meta_interesting, dtype=np.bool_)
    num_actions_arr = np.array(meta_num_actions, dtype=np.int16)
    num_play_arr = np.array(meta_num_play, dtype=np.int16)
    num_give_arr = np.array(meta_num_give, dtype=np.int16)
    cont_legal_arr = np.array(meta_cont_legal, dtype=np.bool_)

    print("Saving:", args.out)
    print("obs:", obs_arr.shape, "mask:", mask_arr.shape, "act:", act_arr.shape)
    print(
        "meta:",
        f"forced={forced_arr.shape}",
        f"interesting={interesting_arr.shape}",
        f"num_actions={num_actions_arr.shape}",
        f"num_play={num_play_arr.shape}",
        f"num_give={num_give_arr.shape}",
        f"cont_legal={cont_legal_arr.shape}",
    )

    print(
        "dataset stats:",
        f"forced_frac={forced_arr.mean():.3f}",
        f"interesting_frac={interesting_arr.mean():.3f}",
        f"cont_legal_frac={cont_legal_arr.mean():.3f}",
        f"num_actions_mean={num_actions_arr.mean():.3f}",
    )

    np.savez_compressed(
        args.out,
        obs=obs_arr,
        mask=mask_arr,
        act=act_arr,
        forced=forced_arr,
        interesting=interesting_arr,
        num_actions=num_actions_arr,
        num_play=num_play_arr,
        num_give=num_give_arr,
        cont_legal=cont_legal_arr,
    )


if __name__ == "__main__":
    main()