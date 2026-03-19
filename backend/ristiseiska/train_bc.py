from __future__ import annotations

import argparse
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim

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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=str, default="dataset.npz")
    ap.add_argument("--epochs", type=int, default=5)
    ap.add_argument("--batch", type=int, default=256)
    ap.add_argument("--lr", type=float, default=3e-4)
    ap.add_argument("--out", type=str, default="policy_bc.pt")
    ap.add_argument("--device", type=str, default="cpu")

    ap.add_argument("--forced-weight", type=float, default=0.5)
    ap.add_argument("--interesting-weight", type=float, default=2.0)
    ap.add_argument("--cont-legal-mult", type=float, default=1.5)

    args = ap.parse_args()

    d = np.load(args.data)

    obs = d["obs"].astype(np.float32)
    mask = d["mask"].astype(np.bool_)
    act = d["act"].astype(np.int64)

    assert obs.shape[1] == OBS_DIM
    assert mask.shape[1] == ACTION_DIM

    N = obs.shape[0]

    # Optional metadata
    forced = d["forced"].astype(np.bool_) if "forced" in d else np.zeros(N, dtype=np.bool_)
    interesting = d["interesting"].astype(np.bool_) if "interesting" in d else np.zeros(N, dtype=np.bool_)
    cont_legal = d["cont_legal"].astype(np.bool_) if "cont_legal" in d else np.zeros(N, dtype=np.bool_)

    weights = np.ones(N, dtype=np.float32)

    # Base weighting
    weights[forced] *= args.forced_weight
    weights[interesting] *= args.interesting_weight
    weights[cont_legal] *= args.cont_legal_mult

    # Normalize mean weight to ~1.0 to keep optimization stable
    weights = weights / max(weights.mean(), 1e-8)

    idx = np.arange(N)
    np.random.shuffle(idx)

    split = int(0.9 * N)
    tr_idx = idx[:split]
    va_idx = idx[split:]

    device = torch.device(args.device)

    model = PolicyNet(OBS_DIM, ACTION_DIM).to(device)
    opt = optim.Adam(model.parameters(), lr=args.lr)
    loss_fn = nn.CrossEntropyLoss(reduction="none")

    def run_epoch(train: bool):
        model.train(train)
        use_idx = tr_idx if train else va_idx

        total_loss = 0.0
        total_acc = 0
        total = 0

        for i in range(0, len(use_idx), args.batch):
            b = use_idx[i:i + args.batch]

            xb = torch.from_numpy(obs[b]).to(device)
            mb = torch.from_numpy(mask[b]).to(device)
            yb = torch.from_numpy(act[b]).to(device)
            wb = torch.from_numpy(weights[b]).to(device)

            logits = model(xb)

            neg_inf = torch.tensor(-1e9, device=device, dtype=logits.dtype)
            logits_masked = torch.where(mb, logits, neg_inf)

            per_sample_loss = loss_fn(logits_masked, yb)
            loss = (per_sample_loss * wb).mean()

            if train:
                opt.zero_grad()
                loss.backward()
                opt.step()

            total_loss += float(loss.item()) * len(b)

            with torch.no_grad():
                pred = torch.argmax(logits_masked, dim=1)
                total_acc += int((pred == yb).sum().item())
                total += len(b)

        return total_loss / max(1, total), total_acc / max(1, total)

    print(
        f"Loaded {N} samples | "
        f"forced_frac={forced.mean():.3f} "
        f"interesting_frac={interesting.mean():.3f} "
        f"cont_legal_frac={cont_legal.mean():.3f} "
        f"mean_weight={weights.mean():.3f}"
    )

    for e in range(1, args.epochs + 1):
        tr_loss, tr_acc = run_epoch(train=True)
        va_loss, va_acc = run_epoch(train=False)
        print(
            f"epoch {e:02d}  "
            f"train loss {tr_loss:.4f} acc {tr_acc:.3f} | "
            f"val loss {va_loss:.4f} acc {va_acc:.3f}"
        )

    torch.save(model.state_dict(), args.out)
    print("Saved:", args.out)


if __name__ == "__main__":
    main()