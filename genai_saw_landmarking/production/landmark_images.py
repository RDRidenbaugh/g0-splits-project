"""Landmark every saw image with the 5 cross-fitted v1.2 models (step 4 of the saw production pipeline).

Reads image_table.csv (prep_images.py) and predicts the 52-point v1.2 configuration on each prepared
image (protocol frame: apex left, teeth up), exactly as the lance v1.4 pipeline does:
  * an image whose label trained the models gets the model it was held out from: source "oof_f<k>";
  * every other image (no label, label dropped in review, or new) gets the 5-model mean: "ensemble".
No image is predicted by a model that trained on it. Exact duplicate files (duplicate_of) are skipped.

QC flags (the image is still written; export_geomorph.py decides):
  label_gap  an out-of-fold prediction is far from the image's own label: mean point distance
             > 2x the median over all out-of-fold images. Either the CNN or the label is wrong:
             look at the overlay (both are drawn)
  spread     the 5 models disagree: mean distance to their mean > 3x the median (ensemble images)
  order      V1..V7 or R1..R7 out of order along the saw (apex -> V1 axis)
  outside    a point off the image
  shape      Procrustes distance to the mean shape is a robust outlier (z > 4)
  no_scale   the image has no usable scale bar (session median used; see ../analysis/data/calibration.csv)

Outputs in --out-dir:
  predictions_px_saw.csv  key, id, side, cohort, session, image, raw_image, mirrored, vflipped, width,
                          height, px_per_mm, cal_source, source, spread_px, label_gap_um, procrustes_d,
                          flags, x1, y1, ... x52, y52 (pixels of the prepared image = protocol frame)
  overlays/<key>.jpg      prediction (and label, if any) drawn on the image (--overlays flagged|all|none)

usage: python landmark_images.py [--overlays flagged] [--workers 2]
Next: python export_geomorph.py
"""
import argparse, csv, json, os, sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
CNN = ROOT.parent / "cnn"  # shared network code
sys.path.insert(0, str(CNN))
sys.path.insert(0, str(ROOT / "tools"))
import torch  # noqa: E402
from torch.utils.data import DataLoader, Dataset  # noqa: E402
from constants import HEATMAP_STRIDE, INPUT_SIZE  # noqa: E402
from dataset import IMAGENET_MEAN, IMAGENET_STD, letterbox, load_rgb  # noqa: E402
from heatmap import dsnt_expectation  # noqa: E402
from model import HeatmapNet  # noqa: E402
import scheme  # noqa: E402

ORDER = [p for p, _ in scheme.point_order()]
IX = {p: i for i, p in enumerate(ORDER)}
SEQS = [[f"V{k}" for k in range(1, 8)], [f"R{k}" for k in range(1, 8)]]  # must run proximal -> distal


class Images(Dataset):
    def __init__(self, rows):
        self.rows = rows

    def __len__(self):
        return len(self.rows)

    def __getitem__(self, i):
        img = load_rgb(str(HERE / self.rows[i]["image"]))
        canvas, scale, px, py = letterbox(img, INPUT_SIZE)
        x = (canvas.astype(np.float32) / 255.0 - IMAGENET_MEAN) / IMAGENET_STD
        return {"image": torch.from_numpy(np.ascontiguousarray(x.transpose(2, 0, 1))), "i": i,
                "scale": scale, "pad": torch.tensor([px, py], dtype=torch.float32), "hw": torch.tensor(img.shape[:2])}


def load_models(runs):
    models, test_keys = [], {}
    for k in range(5):
        d = runs / f"saw_f{k}"
        if not (d / "best.pt").exists():
            continue
        state = torch.load(d / "best.pt", map_location="cpu")
        n = [v.shape[0] for key, v in state.items() if key.endswith("weight") and v.dim() == 4][-1]
        m = HeatmapNet(n, pretrained=False)
        m.load_state_dict(state)
        m.eval()
        models.append((k, m))
        for key in json.load(open(d / "split_keys.json"))["test"]:
            test_keys[key] = len(models) - 1
    return models, test_keys


def order_ok(P):
    p0, p1 = P[IX["V1"]], P[IX["S01"]]
    u = (p1 - p0) / (np.linalg.norm(p1 - p0) + 1e-9)
    return all(np.all(np.diff((P[[IX[q] for q in seq]] - p0) @ u) > 0) for seq in SEQS)


def procrustes_dist(configs):
    X = np.array([c - c.mean(0) for c in configs])
    X /= np.linalg.norm(X, axis=(1, 2), keepdims=True)
    ref = X[0]
    for _ in range(5):
        for i in range(len(X)):
            U, _, Vt = np.linalg.svd(X[i].T @ ref)
            if np.linalg.det(U @ Vt) < 0:
                U[:, -1] *= -1
            X[i] = X[i] @ (U @ Vt)
        ref = X.mean(0) / np.linalg.norm(X.mean(0))
    return np.linalg.norm(X - ref, axis=(1, 2))


def robust_z(v):
    med = np.median(v)
    return (v - med) / (np.median(np.abs(v - med)) * 1.4826 + 1e-12)


def draw_overlay(row, P, path, label=None):
    """Prediction on the prepared image, cropped to the saw: anchors red with IDs, semilandmarks yellow;
    a label (if any) in cyan with a white line to each predicted point."""
    from PIL import Image, ImageDraw
    img = Image.fromarray(load_rgb(str(HERE / row["image"])))
    pts = P if label is None else np.vstack([P, label])
    x0, y0 = np.maximum(pts.min(0) - 120, 0)
    x1, y1 = np.minimum(pts.max(0) + 120, [img.width, img.height])
    img = img.crop((int(x0), int(y0), int(x1), int(y1)))
    s = 1400 / max(img.size)
    img = img.resize((round(img.width * s), round(img.height * s)))
    d = ImageDraw.Draw(img)
    to = lambda q: (np.asarray(q) - [x0, y0]) * s  # noqa: E731
    if label is not None:
        for a, b in zip(to(label), to(P)):
            d.line([tuple(a), tuple(b)], fill=(255, 255, 255), width=1)
            d.ellipse([a[0] - 4, a[1] - 4, a[0] + 4, a[1] + 4], outline=(0, 200, 255), width=2)
    for pid, q in zip(ORDER, to(P)):
        semi = ":" in pid
        col = (230, 170, 0) if semi else (230, 30, 30)
        r = 3 if semi else 5
        d.ellipse([q[0] - r, q[1] - r, q[0] + r, q[1] + r], outline=col, width=2)
        if not semi:
            d.text((q[0] + 6, q[1] - 14), pid, fill=col)
    gap = f"  label gap {row['label_gap_um']} um (cyan = label)" if label is not None else ""
    d.text((8, 8), f"{row['key']}  {row['source']}  {row['flags'] or 'ok'}{gap}", fill=(0, 0, 0))
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path, quality=85)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--table", default=str(HERE / "image_table.csv"))
    ap.add_argument("--manifest", default=str(HERE / "manifest_saw_v12.csv"))
    ap.add_argument("--runs", default=str(HERE / "runs" / "v12"))
    ap.add_argument("--out-dir", default=str(HERE / "output"))
    ap.add_argument("--overlays", choices=["flagged", "all", "none"], default="flagged")
    ap.add_argument("--batch-size", type=int, default=8)
    ap.add_argument("--workers", type=int, default=2)
    a = ap.parse_args()
    torch.set_num_threads(int(os.environ.get("OMP_NUM_THREADS", os.cpu_count() or 1)))
    out = Path(a.out_dir)
    out.mkdir(parents=True, exist_ok=True)

    rows = [r for r in csv.DictReader(open(a.table)) if not r["duplicate_of"]]
    labels = {r["key"]: np.array(json.loads(r["landmarks_px_json"])) for r in csv.DictReader(open(a.manifest))}
    models, test_keys = load_models(Path(a.runs))
    if len(models) < 5:
        print(f"warning: {len(models)} of 5 models found in {a.runs}")
    n = len(ORDER)
    preds = np.zeros((len(rows), n, 2))
    spread = np.zeros(len(rows))
    loader = DataLoader(Images(rows), batch_size=a.batch_size, num_workers=a.workers)
    with torch.no_grad():
        for b in loader:
            allp = []
            for _, m in models:
                xy = dsnt_expectation(m(b["image"]))[0] * HEATMAP_STRIDE
                allp.append(((xy - b["pad"][:, None]) / b["scale"][:, None, None].float()).numpy())
            allp = np.stack(allp)  # models x batch x n x 2
            for j, i in enumerate(b["i"].tolist()):
                r = rows[i]
                r["height"], r["width"] = b["hw"][j].tolist()
                mean = allp[:, j].mean(0)
                spread[i] = np.linalg.norm(allp[:, j] - mean, axis=-1).mean()
                if r["key"] in test_keys:
                    k = test_keys[r["key"]]
                    preds[i], r["source"] = allp[k, j], f"oof_f{models[k][0]}"
                elif r["key"] in labels:  # its held-out model is missing: every model saw it
                    preds[i], r["source"] = mean, "in_sample"
                else:
                    preds[i], r["source"] = mean, "ensemble"

    # QC
    ppm = np.array([float(r["px_per_mm"]) if r["px_per_mm"] else np.nan for r in rows])
    gaps_px = {i: np.linalg.norm(preds[i] - labels[r["key"]], axis=1).mean()
               for i, r in enumerate(rows) if r["source"].startswith("oof") and r["key"] in labels}
    gap_lim = 2 * np.median(list(gaps_px.values())) if gaps_px else np.inf
    ens = np.array([r["source"] == "ensemble" for r in rows])
    med_spread = max(0.5, np.median(spread[ens]) if ens.any() else np.median(spread))
    zs = robust_z(procrustes_dist(list(preds)))
    pd_ = procrustes_dist(list(preds))
    for i, r in enumerate(rows):
        f = []
        if i in gaps_px and gaps_px[i] > gap_lim:
            f.append("label_gap")
        if r["source"] == "in_sample":
            f.append("in_sample")
        if ens[i] and spread[i] > 3 * med_spread:
            f.append("spread")
        if not order_ok(preds[i]):
            f.append("order")
        P = preds[i]
        if (P < 0).any() or (P[:, 0] > r["width"]).any() or (P[:, 1] > r["height"]).any():
            f.append("outside")
        if zs[i] > 4:
            f.append("shape")
        if r["cal_source"] != "own_bar":
            f.append("no_scale")
        r.update(spread_px=round(spread[i], 2), procrustes_d=round(pd_[i], 5), flags=";".join(f),
                 label_gap_um=round(gaps_px[i] / ppm[i] * 1000, 1) if i in gaps_px and ppm[i] == ppm[i] else "")

    cols = ["key", "id", "side", "cohort", "session", "image", "raw_image", "mirrored", "vflipped", "width", "height",
            "px_per_mm", "cal_source", "source", "spread_px", "label_gap_um", "procrustes_d", "flags"]
    with open(out / "predictions_px_saw.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(cols + [f"{c}{k}" for k in range(1, n + 1) for c in "xy"])
        for i, r in enumerate(rows):
            w.writerow([r.get(c, "") for c in cols] + [round(v, 2) for v in preds[i].ravel()])

    if a.overlays != "none":
        for i, r in enumerate(rows):
            if a.overlays == "all" or r["flags"]:
                draw_overlay(r, preds[i], out / "overlays" / f"{r['key']}.jpg", labels.get(r["key"]))
    from collections import Counter
    src = Counter(r["source"].split("_")[0] for r in rows)
    fl = Counter(x for r in rows for x in r["flags"].split(";") if x)
    print(f"{len(rows)} images, {len(models)} models: {dict(src)}; flagged {sum(bool(r['flags']) for r in rows)} {dict(fl)}")
    print(f"label_gap limit {gap_lim / np.nanmedian(ppm) * 1000:.1f} um (2x the median out-of-fold gap)")


if __name__ == "__main__":
    main()
