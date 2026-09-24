"""Export manual + model-predicted landmarks for the DSNT test-set individuals,
in a wide-format CSV geomorph can read directly: ID, Group, X1, Y1, X2, Y2, ...

Step 6a (see project docs): lets R compare manual vs. predicted shape via GPA/
Procrustes without re-deriving anything -- both CSVs share the same row order,
same individuals, same landmark order, same (original-image) pixel units.
Only the test split is exported (never seen in training), matching train.py's
default split (val_frac=0.15, test_frac=0.15, seed=42) unless overridden.

Usage (from lance_landmarking/model/, with the project venv active):
    python3 export_predictions.py --angle Right --checkpoint runs/21ix26_runs/Right_36764579/best.pt
    python3 export_predictions.py --angle Left   --checkpoint runs/21ix26_runs/Left_36764579/best.pt
    python3 export_predictions.py --angle Bottom --checkpoint runs/21ix26_runs/Bottom_36764579/best.pt
"""
from __future__ import annotations

import argparse
import csv
import os
import sys
from pathlib import Path

import torch
from torch.utils.data import DataLoader

sys.path.insert(0, str(Path(__file__).parent.parent / "tools"))
from landmarks_io import read_image_meta  # noqa: E402

from constants import EXPECTED_N, HEATMAP_STRIDE, MANIFEST_PATH
from dataset import LanceLandmarkDataset
from heatmap import dsnt_expectation
from model import HeatmapNet
from splits import load_clean_samples, split_samples


def landmark_columns(n: int) -> list[str]:
    cols = []
    for i in range(1, n + 1):
        cols += [f"X{i}", f"Y{i}"]
    return cols


def flatten(points) -> list:
    out = []
    for x, y in points:
        out += [x, y]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--angle", required=True, choices=list(EXPECTED_N))
    ap.add_argument("--checkpoint", required=True)
    ap.add_argument("--manifest", default=str(Path(__file__).parent.parent / MANIFEST_PATH))
    ap.add_argument("--val-frac", type=float, default=0.15)
    ap.add_argument("--test-frac", type=float, default=0.15)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--batch-size", type=int, default=8)
    ap.add_argument("--out-dir", default=str(Path(__file__).parent.parent / "analysis" / "data"))
    ap.add_argument("--suffix", default="", help="appended to output file names, e.g. _newproto")
    args = ap.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    samples = load_clean_samples(args.manifest, args.angle)
    _train_s, _val_s, test_s = split_samples(samples, args.val_frac, args.test_frac, args.seed)
    print(f"[{args.angle}] test individuals: {len(test_s)}")
    if not test_s:
        print("No test samples -- nothing to export.")
        return
    n = test_s[0].n_expected  # from the labels, so other protocols work unchanged

    ds = LanceLandmarkDataset(test_s)
    loader = DataLoader(ds, batch_size=args.batch_size, shuffle=False, num_workers=0)

    n_threads = int(os.environ.get("SLURM_CPUS_PER_TASK", os.environ.get("OMP_NUM_THREADS", os.cpu_count() or 1)))
    torch.set_num_threads(n_threads)

    model = HeatmapNet(n, pretrained=False)
    model.load_state_dict(torch.load(args.checkpoint, map_location="cpu"))
    model.eval()

    manual_rows, pred_rows = [], []
    meta_cache = {}
    with torch.no_grad():
        for batch in loader:
            preds = model(batch["image"])
            pred_hm_xy = dsnt_expectation(preds)[0]  # (B, K, 2) heatmap-pixel space
            pred_input_px = pred_hm_xy * HEATMAP_STRIDE  # INPUT_SIZE-space

            scale = batch["scale"]
            pad = batch["pad"]
            gt_input_px = batch["landmarks_input_px"]

            for b in range(len(batch["key"])):
                s = scale[b].item()
                px0, py0 = pad[b].tolist()
                pred_orig = ((pred_input_px[b] - torch.tensor([px0, py0])) / s).tolist()
                gt_orig = ((gt_input_px[b] - torch.tensor([px0, py0])) / s).tolist()

                marked_tiff = batch["marked_tiff"][b]
                if marked_tiff not in meta_cache:
                    try:
                        meta = read_image_meta(marked_tiff)
                        meta_cache[marked_tiff] = meta.px_per_unit if meta.unit == "mm" else None
                    except Exception:
                        meta_cache[marked_tiff] = None
                px_per_mm = meta_cache[marked_tiff]

                key, group = batch["key"][b], batch["group"][b]
                manual_rows.append([key, group, px_per_mm, *flatten(gt_orig)])
                pred_rows.append([key, group, px_per_mm, *flatten(pred_orig)])

    header = ["ID", "Group", "px_per_mm", *landmark_columns(n)]
    for name, rows in (("manual", manual_rows), ("predicted", pred_rows)):
        out_path = out_dir / f"{args.angle}_{name}_test{args.suffix}.csv"
        with open(out_path, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(header)
            w.writerows(rows)
        print(f"wrote {len(rows)} rows -> {out_path}")


if __name__ == "__main__":
    main()
