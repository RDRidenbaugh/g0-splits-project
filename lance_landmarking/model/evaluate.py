"""Evaluate a trained HeatmapNet checkpoint on its held-out test split,
reporting per-landmark error in both pixels and millimeters (using each
image's own ImageJ calibration, since that differs by camera session).

Usage:
    python3 evaluate.py --angle Bottom --checkpoint runs/Bottom/best.pt
"""
from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
from pathlib import Path

import torch
from torch.utils.data import DataLoader

sys.path.insert(0, str(Path(__file__).parent.parent / "tools"))
from landmarks_io import read_image_meta  # noqa: E402

from constants import EXPECTED_N, HEATMAP_STRIDE, MANIFEST_PATH
from dataset import LanceLandmarkDataset
from heatmap import dsnt_expectation, soft_argmax_decode
from model import HeatmapNet
from splits import load_clean_samples, split_samples


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--angle", required=True, choices=list(EXPECTED_N))
    ap.add_argument("--checkpoint", required=True)
    ap.add_argument("--manifest", default=str(Path(__file__).parent.parent / MANIFEST_PATH))
    ap.add_argument("--val-frac", type=float, default=0.15)
    ap.add_argument("--test-frac", type=float, default=0.15)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--batch-size", type=int, default=8)
    ap.add_argument("--loss", choices=["mse", "dsnt"], default="mse",
                    help="how the checkpoint was trained; dsnt decodes with the soft-argmax expectation instead of the peak window")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    samples = load_clean_samples(args.manifest, args.angle)
    _train_s, _val_s, test_s = split_samples(samples, args.val_frac, args.test_frac, args.seed)
    print(f"[{args.angle}] test samples: {len(test_s)}")
    if not test_s:
        print("No test samples -- nothing to evaluate.")
        return

    ds = LanceLandmarkDataset(test_s)
    loader = DataLoader(ds, batch_size=args.batch_size, shuffle=False, num_workers=0)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if device.type == "cpu":
        n_threads = int(os.environ.get("SLURM_CPUS_PER_TASK", os.environ.get("OMP_NUM_THREADS", os.cpu_count() or 1)))
        torch.set_num_threads(n_threads)
    n_lm = test_s[0].n_expected  # from the labels, so other protocols work unchanged
    model = HeatmapNet(n_lm, pretrained=False).to(device)
    model.load_state_dict(torch.load(args.checkpoint, map_location=device))
    model.eval()

    px_errors_per_landmark = [[] for _ in range(n_lm)]
    mm_errors_per_landmark = [[] for _ in range(n_lm)]
    per_image = []

    meta_cache = {}
    with torch.no_grad():
        for batch in loader:
            images = batch["image"].to(device)
            preds = model(images)  # (B, K, Hh, Wh)
            if args.loss == "dsnt":
                pred_hm_xy = dsnt_expectation(preds.cpu())[0]  # (B, K, 2) heatmap-pixel space
            else:
                pred_hm_xy = soft_argmax_decode(preds.cpu())  # (B, K, 2) heatmap-pixel space

            scale = batch["scale"]  # (B,)
            pad = batch["pad"]  # (B, 2)
            gt_input_px = batch["landmarks_input_px"]  # (B, K, 2) INPUT_SIZE space
            valid = batch["valid"]  # (B, K)

            pred_input_px = pred_hm_xy * HEATMAP_STRIDE  # back to INPUT_SIZE space

            for b in range(images.shape[0]):
                s = scale[b].item()
                px0, py0 = pad[b].tolist()
                pred_orig = (pred_input_px[b] - torch.tensor([px0, py0])) / s
                gt_orig = (gt_input_px[b] - torch.tensor([px0, py0])) / s
                err_px = torch.linalg.norm(pred_orig - gt_orig, dim=-1)  # (K,)

                marked_tiff = batch["marked_tiff"][b]
                if marked_tiff not in meta_cache:
                    try:
                        meta = read_image_meta(marked_tiff)
                        meta_cache[marked_tiff] = meta.px_per_unit if meta.unit == "mm" else None
                    except Exception:
                        meta_cache[marked_tiff] = None
                px_per_mm = meta_cache[marked_tiff]

                v = valid[b]
                img_px_errs = []
                for k in range(n_lm):
                    if not v[k]:
                        continue
                    e_px = err_px[k].item()
                    px_errors_per_landmark[k].append(e_px)
                    img_px_errs.append(e_px)
                    if px_per_mm:
                        mm_errors_per_landmark[k].append(e_px / px_per_mm)
                per_image.append(
                    {
                        "key": batch["key"][b],
                        "group": batch["group"][b],
                        "mean_px_error": statistics.mean(img_px_errs) if img_px_errs else None,
                    }
                )

    all_px = [e for lm in px_errors_per_landmark for e in lm]
    all_mm = [e for lm in mm_errors_per_landmark for e in lm]

    summary = {
        "angle": args.angle,
        "n_test_images": len(test_s),
        "n_landmark_observations": len(all_px),
        "mean_px_error": statistics.mean(all_px) if all_px else None,
        "median_px_error": statistics.median(all_px) if all_px else None,
        "mean_mm_error": statistics.mean(all_mm) if all_mm else None,
        "median_mm_error": statistics.median(all_mm) if all_mm else None,
        "per_landmark_mean_px_error": [
            statistics.mean(lm) if lm else None for lm in px_errors_per_landmark
        ],
    }
    print(json.dumps({k: v for k, v in summary.items() if k != "per_landmark_mean_px_error"}, indent=2))

    out_path = Path(args.out or (Path(args.checkpoint).parent / "eval_test.json"))
    with open(out_path, "w") as f:
        json.dump({**summary, "per_image": per_image}, f, indent=2)
    print(f"Wrote full evaluation to {out_path}")


if __name__ == "__main__":
    main()
