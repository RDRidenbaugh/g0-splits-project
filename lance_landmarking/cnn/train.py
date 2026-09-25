"""Train one HeatmapNet for one view (Bottom/Left/Right).

Usage (from lance_landmarking/cnn/, with the repo venv active):
    python3 train.py --angle Bottom --epochs 40
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import torch
from torch.utils.data import DataLoader

from constants import EXPECTED_N, HEATMAP_STRIDE, MANIFEST_PATH
from dataset import LanceLandmarkDataset
from heatmap import dsnt_expectation
from model import HeatmapNet
from splits import fold_split, load_clean_samples, split_samples


def heatmap_loss(pred: torch.Tensor, target: torch.Tensor, valid: torch.Tensor, fg_weight: float = 0.0) -> torch.Tensor:
    """Masked MSE. fg_weight > 0 upweights pixels near a landmark by
    (1 + fg_weight * target): plain MSE on tiny Gaussian blobs is dominated by
    background, so predicting all-zeros is a strong local minimum (loss ~=
    pi*sigma^2/H^2 = 0.000767) that some runs never leave."""
    # pred/target: (B, K, H, W); valid: (B, K)
    diff2 = (1.0 + fg_weight * target) * (pred - target) ** 2
    per_channel = diff2.mean(dim=(2, 3))  # (B, K)
    mask = valid.float()
    denom = mask.sum().clamp(min=1)
    return (per_channel * mask).sum() / denom


def dsnt_loss(pred, target, valid, gt_xy, lam: float = 1.0):
    """DSNT: Euclidean error of the soft-argmax position (scaled to ~[0,1] by
    half the map width) + lam * Jensen-Shannon divergence between the predicted
    spatial softmax and the normalized Gaussian target (keeps each map
    unimodal so the expectation is meaningful).
    gt_xy: (B, K, 2) true landmark position in heatmap pixels.
    Returns (loss, mean position error in heatmap pixels), both over valid channels."""
    xy, prob = dsnt_expectation(pred)
    half_w = pred.shape[-1] / 2
    dist = torch.sqrt(((xy - gt_xy) ** 2).sum(dim=-1) + 1e-8)  # (B, K)
    q = target.flatten(2)
    q = (q / q.sum(dim=-1, keepdim=True).clamp(min=1e-8)).view_as(prob)
    pe, qe = prob.clamp(min=1e-8), q.clamp(min=1e-8)
    m = 0.5 * (pe + qe)
    js = 0.5 * ((pe * (pe / m).log()).sum(dim=(2, 3)) + (qe * (qe / m).log()).sum(dim=(2, 3)))
    per = dist / half_w + lam * js
    mask = valid.float()
    denom = mask.sum().clamp(min=1)
    return (per * mask).sum() / denom, (dist * mask).sum() / denom


def run_epoch(model, loader, optimizer, device, train: bool, fg_weight: float = 0.0, lr_at=None, step0: int = 0,
              loss_type: str = "mse", lam: float = 1.0):
    """Returns mean objective loss, mean plain (unweighted) MSE, and mean peak
    of the predicted heatmaps. Peak ~0 means the network is outputting blank
    heatmaps (collapse); a healthy run sits near the target peak of ~1."""
    model.train(mode=train)
    tot_loss = tot_mse = tot_peak = tot_err = 0.0
    n_batches, step = 0, step0
    with torch.set_grad_enabled(train):
        for batch in loader:
            images = batch["image"].to(device)
            targets = batch["heatmaps"].to(device)
            valid = batch["valid"].to(device)
            preds = model(images)
            if loss_type == "dsnt":
                gt_xy = batch["landmarks_input_px"].to(device) / HEATMAP_STRIDE
                loss, err_hm = dsnt_loss(preds, targets, valid, gt_xy, lam)
                tot_err += err_hm.item() * HEATMAP_STRIDE  # -> pixels of the 512 network input
            else:
                loss = heatmap_loss(preds, targets, valid, fg_weight)
            if train:
                if lr_at is not None:
                    for g in optimizer.param_groups:
                        g["lr"] = lr_at(step)
                optimizer.zero_grad()
                loss.backward()
                optimizer.step()
                step += 1
            with torch.no_grad():
                if loss_type != "dsnt":  # blank-floor MSE is meaningless for softmax-trained maps
                    tot_mse += heatmap_loss(preds, targets, valid, 0.0).item()
                m = valid.float()
                tot_peak += ((preds.amax(dim=(2, 3)) * m).sum() / m.sum().clamp(min=1)).item()
            tot_loss += loss.item()
            n_batches += 1
    n = max(1, n_batches)
    return {"loss": tot_loss / n, "mse": tot_mse / n, "peak": tot_peak / n,
            "err": tot_err / n if loss_type == "dsnt" else float("nan")}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--angle", required=True, choices=list(EXPECTED_N))
    ap.add_argument("--manifest", default=str(Path(__file__).parent / MANIFEST_PATH))
    ap.add_argument("--epochs", type=int, default=40)
    ap.add_argument("--batch-size", type=int, default=8)
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--val-frac", type=float, default=0.15)
    ap.add_argument("--test-frac", type=float, default=0.15)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--folds", default=None,
                    help="cross-fitting: JSON {family: fold}; test = --fold's families, val drawn from the rest")
    ap.add_argument("--fold", type=int, default=None)
    ap.add_argument("--no-pretrained", action="store_true")
    ap.add_argument("--num-workers", type=int, default=2)
    ap.add_argument("--out-dir", default=None)
    ap.add_argument("--limit", type=int, default=None, help="debug: cap total samples")
    ap.add_argument("--resume", action="store_true",
                    help="continue an interrupted run from <out-dir>/last.pt (weights + optimizer + epoch + history); --epochs is the TOTAL target")
    ap.add_argument("--init-weights", default=None,
                    help="start from model weights only (e.g. an old best.pt); optimizer and epoch counter start fresh")
    ap.add_argument("--loss", choices=["mse", "dsnt"], default="mse",
                    help="mse: Gaussian heatmap regression (can stall at an all-zeros solution); dsnt: soft-argmax coordinate loss")
    ap.add_argument("--dsnt-lambda", type=float, default=1.0, help="weight of the JS-divergence regularizer in --loss dsnt")
    ap.add_argument("--cache-images", action="store_true", help="keep decoded/letterboxed images in RAM after first read")
    ap.add_argument("--fg-weight", type=float, default=0.0,
                    help="foreground upweighting k in loss weight (1 + k*target); 0 = plain MSE")
    ap.add_argument("--lr-decay", choices=["none", "cosine"], default="none",
                    help="cosine: decay lr from --lr to ~1%% of it over --epochs (constant lr made val error bounce between epochs)")
    ap.add_argument("--warmup-epochs", type=float, default=0.0,
                    help="linear LR warmup from ~0 to --lr over this many epochs")
    ap.add_argument("--collapse-after", type=int, default=15,
                    help="abort if val heatmap peak is still below --collapse-peak at/after this epoch (0 = disable)")
    ap.add_argument("--collapse-peak", type=float, default=0.05)
    args = ap.parse_args()

    out_dir = Path(args.out_dir or (Path(__file__).parent / "runs" / args.angle.lower()))
    out_dir.mkdir(parents=True, exist_ok=True)

    samples = load_clean_samples(args.manifest, args.angle)
    if args.limit:
        samples = samples[: args.limit]
    if args.folds:
        folds = json.load(open(args.folds))
        train_s, val_s, test_s = fold_split(samples, folds, args.fold, args.val_frac, args.seed)
    else:
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

    train_ds = LanceLandmarkDataset(train_s, cache=args.cache_images)
    val_ds = LanceLandmarkDataset(val_s, cache=args.cache_images)
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
    # landmark count comes from the labels (EXPECTED_N for the v2 manifest; other protocols via --manifest)
    model = HeatmapNet(samples[0].n_expected, pretrained=not args.no_pretrained).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=args.lr)

    steps_per_epoch = max(1, len(train_loader))
    warmup_steps = int(args.warmup_epochs * steps_per_epoch)
    total_steps = max(1, args.epochs * steps_per_epoch)

    def lr_at(st):
        f = min(1.0, (st + 1) / warmup_steps) if warmup_steps > 0 else 1.0
        if args.lr_decay == "cosine":
            f *= 0.01 + 0.99 * 0.5 * (1 + math.cos(math.pi * min(1.0, st / total_steps)))
        return args.lr * f
    if warmup_steps == 0 and args.lr_decay == "none":
        lr_at = None

    history = {"train_loss": [], "val_loss": [], "val_mse": [], "val_peak": [], "val_err": []}
    best_val = float("inf")
    start_epoch = 0
    ckpt_path = out_dir / "last.pt"
    if args.resume:
        ckpt = torch.load(ckpt_path, map_location=device)
        model.load_state_dict(ckpt["model"])
        optimizer.load_state_dict(ckpt["optimizer"])
        history, best_val, start_epoch = ckpt["history"], ckpt["best_val"], ckpt["epoch"]
        for k in ("val_mse", "val_peak", "val_err"):  # runs from before these were logged
            history.setdefault(k, [float("nan")] * start_epoch)
        print(f"Resumed from {ckpt_path}: {start_epoch} epochs done, best_val={best_val:.5f}")
    elif args.init_weights:
        model.load_state_dict(torch.load(args.init_weights, map_location=device))
        print(f"Initialized weights from {args.init_weights} (optimizer/epoch counter fresh)")

    collapsed = False
    for epoch in range(start_epoch + 1, args.epochs + 1):
        t0 = time.time()
        tr = run_epoch(model, train_loader, optimizer, device, train=True, fg_weight=args.fg_weight,
                       lr_at=lr_at, step0=(epoch - 1) * steps_per_epoch, loss_type=args.loss, lam=args.dsnt_lambda)
        nan = float("nan")
        va = run_epoch(model, val_loader, optimizer, device, train=False, fg_weight=args.fg_weight,
                       loss_type=args.loss, lam=args.dsnt_lambda) \
            if len(val_ds) else {"loss": nan, "mse": nan, "peak": nan, "err": nan}
        train_loss, val_loss = tr["loss"], va["loss"]
        history["train_loss"].append(train_loss)
        history["val_loss"].append(val_loss)
        history["val_mse"].append(va["mse"])
        history["val_peak"].append(va["peak"])
        history["val_err"].append(va["err"])
        dt = time.time() - t0
        print(f"epoch {epoch:3d}/{args.epochs}  train_loss={train_loss:.5f}  val_loss={val_loss:.5f}  "
              f"val_mse={va['mse']:.6f}  val_peak={va['peak']:.3f}  val_err_px={va['err']:.2f}  lr={optimizer.param_groups[0]['lr']:.2e}  ({dt:.1f}s)")
        select = va["err"] if args.loss == "dsnt" else val_loss   # dsnt: pick the checkpoint with the lowest val position error
        if select < best_val:
            best_val = select
            torch.save(model.state_dict(), out_dir / "best.pt")
        # every epoch, so a walltime kill loses at most one epoch. Write to a
        # temp file then rename: a kill mid-write can't corrupt the checkpoint.
        tmp = out_dir / "last.pt.tmp"
        torch.save(
            {"model": model.state_dict(), "optimizer": optimizer.state_dict(),
             "epoch": epoch, "best_val": best_val, "history": history},
            tmp,
        )
        os.replace(tmp, ckpt_path)
        with open(out_dir / "history.json", "w") as f:
            json.dump(history, f, indent=2)
        if args.loss == "mse" and args.collapse_after and epoch >= args.collapse_after and va["peak"] < args.collapse_peak:
            print(f"COLLAPSE: val heatmap peak {va['peak']:.4f} < {args.collapse_peak} at epoch {epoch} -- "
                  f"network is outputting blank heatmaps (plain-MSE floor is ~0.000767). Aborting.")
            collapsed = True
            break

    plt.figure()
    plt.plot(history["train_loss"], label="train")
    plt.plot(history["val_loss"], label="val")
    plt.xlabel("epoch")
    plt.ylabel("masked heatmap MSE")
    plt.title(f"{args.angle} training curve")
    plt.legend()
    plt.savefig(out_dir / "loss_curve.png", dpi=150)
    print(f"Saved checkpoints + history + loss curve to {out_dir}")
    if collapsed:
        sys.exit(3)  # nonzero: stops the SLURM script before it evaluates a blank model


if __name__ == "__main__":
    main()
