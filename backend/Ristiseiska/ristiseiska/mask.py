from __future__ import annotations

import numpy as np

from .actions import ACTION_DIM, encode_action
from .moves import available_actions
from .state import GameState


def legal_action_mask(state: GameState, player: int) -> np.ndarray:
    mask = np.zeros((ACTION_DIM,), dtype=np.bool_)
    for a in available_actions(state, player):
        mask[encode_action(a)] = True
    return mask
