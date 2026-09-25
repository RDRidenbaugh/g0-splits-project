"""Landmark lance images with the production v1.4 models (step 1 of 2).

Finds every TIFF under the given paths, reads the view from the file name
(..._R.tif, ..._L2.tif, ..._ B11.tif), and predicts the full v1.4 configuration
(Right 42, Left 40, Bottom 38 points) with the 5 cross-fitted models of that view:

  * an image that was in a model's held-out fold (its label trained the other 4)
    gets that model's prediction: source "oof_f<k>" (out-of-fold, never seen);
  * any other image (label failed QC, never digitized, or new) gets the mean of
    the 5 models: source "ensemble".

Either way no image is predicted by a model that trained on it, so the mapping
population and new images are phenotyped the same way.

QC flags written per image (the image is still exported; step 2 decides):
  spread      the 5 models disagree: mean distance to their mean > 3x the view's median
  order       sutures / window ends out of order along the lance's axis
  outside     a point off the image
  shape       Procrustes distance to the view's mean shape is a robust outlier (z > 4)
  no_scale    image width has no known calibration and no --px-per-mm was given
  in_sample   a trained image whose held-out model is missing (all models saw it)

Outputs in --out-dir:
  predictions_px_<View>.csv   ID, key, view, group, image, width, height, px_per_mm,
                              session, source, spread_px, flags, x1, y1, ... (image pixels)
  unparsed_images.txt         files whose name gives no view
  overlays/<View>/<key>.jpg   points drawn on the image (--overlays flagged|all|none)

usage: python landmark_images.py [paths ...] [--out-dir DIR] [--group GROUP] [--px-per-mm N]
  default paths: lance_landmarking/raw_images (the whole mapping population)
Next: python export_geomorph.py --pred-dir DIR
"""
import argparse, csv, json, os, re, sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
CNN = REPO / "lance_landmarking" / "cnn"
sys.path.insert(0, str(CNN))
import torch  # noqa: E402
from torch.utils.data import DataLoader, Dataset  # noqa: E402
from constants import HEATMAP_STRIDE, INPUT_SIZE  # noqa: E402
from dataset import IMAGENET_MEAN, IMAGENET_STD, letterbox, load_rgb  # noqa: E402
from heatmap import dsnt_expectation  # noqa: E402
from model import HeatmapNet  # noqa: E402

SCHEMA = json.load(open(HERE.parent / "landmark_schema.json"))
VIEWS = {"R": "Right", "L": "Left", "B": "Bottom"}
NAME_RE = re.compile(r"^(?P<id>.+?)[_ ]+(?P<view>[RLB])(?P<frame>\d*)$", re.I)
# ImageJ calibration of the two imaging sessions (read from the marked TIFFs; one per camera)
PX_PER_MM = {3840: 927.0, 2560: 1260.0}
GROUP_DIRS = {"lbx": "LBX", "pbx": "PBX", "f1": "F1", "parents": "Parents", "non_laying_parents": "Non_Laying_Parents"}
# (view, sequence that must run proximal -> distal along the lance's axis)
ORDER = {
    "Right": [[f"R{i:02d}" for i in range(4, 11)], [f"R{i:02d}" for i in range(11, 18)]],
    "Left": [[f"L{i:02d}" for i in range(4, 11)], [f"L{i:02d}" for i in range(11, 18)]],
    "Bottom": [["B06", "B05", "B04", "B03"], ["B10", "B09", "B08", "B07"]],
}
AXIS = {"Right": ("R02", "R01"), "Left": ("L02", "L01"), "Bottom": ("B11", ("B01", "B02"))}


def find_images(paths):
    out = []
    for p in map(Path, paths):
        files = [p] if p.is_file() else sorted(q for q in p.rglob("*") if q.is_file())
        out += [f.resolve() for f in files if f.suffix.lower() in (".tif", ".tiff") and ":Zone" not in f.name]
    return out


def manifest_index():
    """raw image path -> (key, group) for images already in the digitized manifest."""
    idx = {}
    for r in csv.DictReader(open(CNN / "manifest.csv")):
        if r["raw_image"]:
            idx[(CNN / r["raw_image"]).resolve()] = (r["key"], r["group"])
    return idx


class Images(Dataset):
    def __init__(self, rows):
        self.rows = rows

    def __len__(self):
        return len(self.rows)

    def __getitem__(self, i):
        img = load_rgb(str(self.rows[i]["path"]))
        canvas, scale, px, py = letterbox(img, INPUT_SIZE)
        x = (canvas.astype(np.float32) / 255.0 - IMAGENET_MEAN) / IMAGENET_STD
        return {"image": torch.from_numpy(np.ascontiguousarray(x.transpose(2, 0, 1))), "i": i,
                "scale": scale, "pad": torch.tensor([px, py], dtype=torch.float32),
                "hw": torch.tensor(img.shape[:2])}


def trained_keys(view):
    """Keys whose labels trained the production models (every one is in exactly one held-out fold)."""
    return {r["key"] for r in csv.DictReader(open(CNN / "manifest_v14.csv")) if r["angle"] == view}


def load_models(view, runs):
    models, test_keys = [], {}
    for k in range(5):
        d = runs / f"{view.lower()}_f{k}"
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


def point_index(view):
    return {p["id"]: i for i, p in enumerate(SCHEMA["views"][view]["points"])}


def axis(view, P, ix):
    a, b = AXIS[view]
    p0 = P[ix[a]]
    p1 = P[[ix[q] for q in b]].mean(0) if isinstance(b, tuple) else P[ix[b]]
    u = p1 - p0
    return p0, u / (np.linalg.norm(u) + 1e-9)


def order_ok(view, P, ix):
    p0, u = axis(view, P, ix)
    for seq in ORDER[view]:
        t = (P[[ix[q] for q in seq]] - p0) @ u
        if np.any(np.diff(t) <= 0):
            return False
    return True


def procrustes_dist(configs):
    """Distance of each configuration to the mean after centring, unit scaling and rotation."""
    X = np.array([c - c.mean(0) for c in configs])
    X /= np.linalg.norm(X, axis=(1, 2), keepdims=True)
    ref = X[0]
    for _ in range(5):
        for i in range(len(X)):
            U, _, Vt = np.linalg.svd(X[i].T @ ref)
            R = U @ Vt
            if np.linalg.det(R) < 0:  # rotation only, no reflection
                U[:, -1] *= -1
                R = U @ Vt
            X[i] = X[i] @ R
        ref = X.mean(0)
        ref /= np.linalg.norm(ref)
    return np.linalg.norm(X - ref, axis=(1, 2))


def robust_z(v):
    med = np.median(v)
    mad = np.median(np.abs(v - med)) * 1.4826 + 1e-12
    return (v - med) / mad


def draw_overlay(row, P, view, path):
    from PIL import Image, ImageDraw
    img = Image.fromarray(load_rgb(str(row["path"])))
    s = 1200 / max(img.size)
    img = img.resize((round(img.width * s), round(img.height * s)))
    d = ImageDraw.Draw(img)
    for p, q in zip(SCHEMA["views"][view]["points"], P * s):
        col = {"anchor": (255, 40, 40), "computed": (40, 140, 255)}.get(p["role"], (255, 220, 0))
        r = 4 if p["role"] != "semilandmark" else 3
        d.ellipse([q[0] - r, q[1] - r, q[0] + r, q[1] + r], outline=col, width=2)
        if p["role"] != "semilandmark":
            d.text((q[0] + 5, q[1] - 12), p["id"], fill=col)
    d.text((8, 8), f"{row['key']}  {row['source']}  {row['flags'] or 'ok'}", fill=(255, 255, 255))
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path, quality=85)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("paths", nargs="*", default=[str(REPO / "lance_landmarking" / "raw_images")])
    ap.add_argument("--out-dir", default=str(HERE / "output"))
    ap.add_argument("--runs", default=str(CNN / "runs" / "v14"), help="folder holding <view>_f<k>/best.pt")
    ap.add_argument("--group", help="cross type for images not in the manifest (default: from the folder name)")
    ap.add_argument("--px-per-mm", type=float, help="calibration for all images (default: by image width)")
    ap.add_argument("--overlays", choices=["flagged", "all", "none"], default="flagged")
    ap.add_argument("--views", default="Right,Left,Bottom")
    ap.add_argument("--batch-size", type=int, default=8)
    ap.add_argument("--workers", type=int, default=2)
    a = ap.parse_args()
    torch.set_num_threads(int(os.environ.get("OMP_NUM_THREADS", os.cpu_count() or 1)))
    out = Path(a.out_dir)
    out.mkdir(parents=True, exist_ok=True)

    idx = manifest_index()
    rows, unparsed = [], []
    for f in find_images(a.paths):
        m = NAME_RE.match(f.stem.strip())
        if not m:
            unparsed.append(str(f))
            continue
        key, group = idx.get(f, (re.sub(r"\s+", "", f.stem).lower(), None))
        group = group or a.group or GROUP_DIRS.get(f.parent.name.lower(), f.parent.name)
        rows.append(dict(path=f, ID=m["id"].strip(), key=key, view=VIEWS[m["view"].upper()], group=group))
    (out / "unparsed_images.txt").write_text("".join(u + "\n" for u in unparsed))
    print(f"{len(rows)} images ({len(unparsed)} without a view in the name: unparsed_images.txt)")

    runs = Path(a.runs)
    for view in a.views.split(","):
        vrows = [r for r in rows if r["view"] == view]
        models, test_keys = load_models(view, runs)
        if not vrows or not models:
            print(f"{view}: {len(vrows)} images, {len(models)} models -- skipped")
            continue
        trained = trained_keys(view)
        ix = point_index(view)
        n = len(ix)
        preds = np.zeros((len(vrows), n, 2))
        spread = np.zeros(len(vrows))
        loader = DataLoader(Images(vrows), batch_size=a.batch_size, num_workers=a.workers)
        with torch.no_grad():
            for b in loader:
                allp = []
                for _, m in models:
                    xy = dsnt_expectation(m(b["image"]))[0] * HEATMAP_STRIDE
                    allp.append(((xy - b["pad"][:, None]) / b["scale"][:, None, None].float()).numpy())
                allp = np.stack(allp)  # models x batch x n x 2
                for j, i in enumerate(b["i"].tolist()):
                    r = vrows[i]
                    r["height"], r["width"] = b["hw"][j].tolist()
                    mean = allp[:, j].mean(0)
                    spread[i] = np.linalg.norm(allp[:, j] - mean, axis=-1).mean()
                    if r["key"] in test_keys:
                        k = test_keys[r["key"]]
                        preds[i], r["source"] = allp[k, j], f"oof_f{models[k][0]}"
                    elif r["key"] in trained:  # its held-out model is missing: every model saw it
                        preds[i], r["source"] = mean, "in_sample"
                    else:
                        preds[i], r["source"] = mean, "ensemble"
        # QC
        pd = procrustes_dist(list(preds))
        zs = robust_z(pd)
        ens = np.array([r["source"] == "ensemble" for r in vrows])
        med_spread = max(0.5, np.median(spread[ens]) if ens.any() else np.median(spread))
        for i, r in enumerate(vrows):
            f = []
            if r["source"] == "in_sample":
                f.append("in_sample")
            if spread[i] > 3 * med_spread:
                f.append("spread")
            if not order_ok(view, preds[i], ix):
                f.append("order")
            P = preds[i]
            if (P < 0).any() or (P[:, 0] > r["width"]).any() or (P[:, 1] > r["height"]).any():
                f.append("outside")
            if zs[i] > 4:
                f.append("shape")
            ppm = a.px_per_mm or PX_PER_MM.get(r["width"])
            if not ppm:
                f.append("no_scale")
            r.update(px_per_mm=ppm or "", session=f"cam{r['width']}", spread_px=round(spread[i], 2),
                     flags=";".join(f), procrustes_d=round(pd[i], 5))
        cols = ["ID", "key", "view", "group", "image", "width", "height", "px_per_mm", "session", "source",
                "spread_px", "procrustes_d", "flags"]
        with open(out / f"predictions_px_{view}.csv", "w", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(cols + [f"{c}{i + 1}" for i in range(n) for c in "xy"])
            for i, r in enumerate(vrows):
                r["image"] = os.path.relpath(r["path"], REPO)
                w.writerow([r[c] for c in cols] + [round(v, 2) for v in preds[i].ravel()])
        nflag = sum(bool(r["flags"]) for r in vrows)
        print(f"{view}: {len(vrows)} images, {len(models)} models, "
              f"{sum(r['source'].startswith('oof') for r in vrows)} out-of-fold, {nflag} flagged "
              f"-> predictions_px_{view}.csv")
        if a.overlays != "none":
            for i, r in enumerate(vrows):
                if a.overlays == "all" or r["flags"]:
                    draw_overlay(r, preds[i], view, out / "overlays" / view / f"{r['key']}.jpg")


if __name__ == "__main__":
    main()
