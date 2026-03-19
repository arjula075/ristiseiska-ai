from __future__ import annotations

import random
import torch
import torch.nn as nn

from ristiseiska.moves import available_actions, Action
from ristiseiska.obs import observe
from ristiseiska.mask import legal_action_mask
from ristiseiska.actions import decode_action


def pick_action_heuristic(actions: list[Action], rng: random.Random) -> Action:
    plays = [a for a in actions if a.kind == "PLAY"]
    if plays:
        return rng.choice(plays)

    gives = [a for a in actions if a.kind == "GIVE"]
    if gives:
        return rng.choice(gives)

    return actions[0]


@torch.no_grad()
def choose_model_action(state, player: int, model: nn.Module, device: str = "cpu") -> Action:
    actions = available_actions(state, player)

    obs = observe(state, player)
    mask = legal_action_mask(state, player)

    x = torch.from_numpy(obs).to(device).unsqueeze(0)
    logits = model(x).squeeze(0)

    mask_t = torch.from_numpy(mask).to(device)
    neg_inf = torch.tensor(-1e9, device=device, dtype=logits.dtype)
    logits_masked = torch.where(mask_t, logits, neg_inf)

    action_id = int(torch.argmax(logits_masked).item())
    action = decode_action(action_id)

    if action not in actions:
        return pick_action_heuristic(actions, random.Random(123))

    return action