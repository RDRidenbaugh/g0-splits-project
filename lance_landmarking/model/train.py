"""Train one HeatmapNet for one view (Bottom/Left/Right).

Usage (from lance_landmarking/model/, with the repo venv active):
    python3 train.py --angle Bottom --epochs 40
"""
from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import torch
from torch.utils.data import DataLoader

from constants import EXPECTED_N, MANIFEST_PATH
from dataset import LanceLandmarkDataset
from model import HeatmapNet
from splits import load_clean_samples, split_samples


def masked_mse(pred: torch.Tensor, target: torch.Tensor, valid: torch.Tensor) -> torch.Tensor:
    # pred/target: (B, K, H, W); valid: (B, K)
    diff2 = (pred - target) ** 2
    per_channel = diff2.mean(dim=(2, 3))  # (B, K)
    mask = valid.float()
    denom = mask.sum().clamp(min=1)
    return (per_channel * mask).sum() / denom


def run_epoch(model, loader, optimizer, device, train: bool):
    model.train(mode=train)
    total_loss, n_batches = 0.0, 0
    with torch.set_grad_enabled(train):
        for batch in loader:
            images = batch["image"].to(device)
            targets = batch["heatmaps"].to(device)
            valid = batch["valid"].to(device)
            preds = model(images)
            loss = masked_mse(preds, targets, valid)
            if train:
                optimizer.zero_grad()
                loss.backward()
                optimizer.step()
            total_loss += loss.item()
            n_batches += 1
    return total_loss / max(1, n_batches)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--angle", required=True, choices=list(EXPECTED_N))
    ap.add_argument("--manifest", default=str(Path(__file__).parent.parent / MANIFEST_PATH))
    ap.add_argument("--epochs", type=int, default=40)
    ap.add_argument("--batch-size", type=int, default=8)
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--val-frac", type=float, default=0.15)
    ap.add_argument("--test-frac", type=float, default=0.15)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--no-pretrained", action="store_true")
    ap.add_argument("--num-workers", type=int, default=2)
    ap.add_argument("--out-dir", default=None)
    ap.add_argument("--limit", type=int, default=None, help="debug: cap total samples")
    args = ap.parse_args()

    out_dir = Path(args.out_dir or (Path(__file__).parent / "runs" / args.angle))
    out_dir.mkdir(parents=True, exist_ok=True)

    samples = load_clean_samples(args.manifest, args.angle)
    if args.limit:
        samples = samples[: args.limit]
    train_s, val_s, test_s = split_samples(samples, args.val_frac, args.test_frac, args.seed)
    print(f"[{args.angle}] samples: train={len(train_s)} val={len(val_s)} test={len(test_s)}")
    with open(out_dir / "split_keys.json", "w") as f:
        json.dump(
            {
                "train": [s.key for s in train_s],
                "val": [s.key for s in val_s],
                "test": [s.key for s in test_s],
            },
            f,
            indent=2,
        )

    train_ds = LanceLandmarkDataset(train_s)
    val_ds = LanceLandmarkDataset(val_s)
    train_loader = DataLoader(train_ds, batch_size=args.batch_size, shuffle=True, num_workers=args.num_workers)
    val_loader = DataLoader(val_ds, batch_size=args.batch_size, shuffle=False, num_workers=args.num_workers)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if device.type == "cpu":
        # belt-and-suspenders: OMP_NUM_THREADS isn't always picked up
        # depending on how this torch build was compiled, and SLURM's
        # cgroup-restricted core count can differ from os.cpu_count()
        n_threads = int(os.environ.get("SLURM_CPUS_PER_TASK", os.environ.get("OMP_NUM_THREADS", os.cpu_count() or 1)))
        torch.set_num_threads(n_threads)
        print(f"CPU training: torch.set_num_threads({n_threads})")
    model = HeatmapNet(EXPECTED_N[args.angle], pretrained=not args.no_pretrained).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=args.lr)

    history = {"train_loss": [], "val_loss": []}
    best_val = float("inf")
    for epoch in range(1, args.epochs + 1):
        t0 = time.time()
        train_loss = run_epoch(model, train_loader, optimizer, device, train=True)
        val_loss = run_epoch(model, val_loader, optimizer, device, train=False) if len(val_ds) else float("nan")
        history["train_loss"].append(train_loss)
        history["val_loss"].append(val_loss)
        dt = time.time() - t0
        print(f"epoch {epoch:3d}/{args.epochs}  train_loss={train_loss:.5f}  val_loss={val_loss:.5f}  ({dt:.1f}s)")
        if val_loss < best_val:
            best_val = val_loss
            torch.save(model.state_dict(), out_dir / "best.pt")
    torch.save(model.state_dict(), out_dir / "last.pt")

    with open(out_dir / "history.json", "w") as f:
        json.dump(history, f, indent=2)

    plt.figure()
    plt.plot(history["train_loss"], label="train")
    plt.plot(history["val_loss"], label="val")
    plt.xlabel("epoch")
    plt.ylabel("masked heatmap MSE")
    plt.title(f"{args.angle} training curve")
    plt.legend()
    plt.savefig(out_dir / "loss_curve.png", dpi=150)
    print(f"Saved checkpoints + history + loss curve to {out_dir}")


if __name__ == "__main__":
    main()
