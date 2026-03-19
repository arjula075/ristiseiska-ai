from __future__ import annotations

from pathlib import Path
import os
import torch
import torch.nn as nn

from ristiseiska.actions import ACTION_DIM
from ristiseiska.obs import OBS_DIM


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


DEFAULT_MODEL_PATH = "models/policy_best_shaped_open7_500k_v2.pt"


def load_policy_model(model_path: str | Path | None = None, device: str = "cpu") -> nn.Module:
    raw_path = model_path or os.getenv("MODEL_PATH") or DEFAULT_MODEL_PATH
    path = Path(raw_path)

    print("Loading model from:", path)

    model = PolicyNet(OBS_DIM, ACTION_DIM)
    state_dict = torch.load(path, map_location=device)
    model.load_state_dict(state_dict)
    model.eval()
    return model