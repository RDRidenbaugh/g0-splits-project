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
              (only informative for ensemble images: 4 of 5 models saw an out-of-fold image)
  label_gap   an out-of-fold prediction is far from the image's own v1.4 label
              (> 2x the typical held-out error). Either the CNN or the label is wrong:
              look at the overlay, which draws both
  order       sutures / window ends out of order along the lance's axis
  outside     a point off the image
  shape       Procrustes distance to the view's mean shape is a robust outlier (z > 4)
  no_scale    no calibration: no --px-per-mm, no NIS-Elements tag, unknown image width
  scale_bar   the burned-in red scale bar is not a round length (10 um ... 5 mm, within 1.5%)
              under the calibration used: wrong calibration or changed zoom
  no_bar      no red scale bar found
  in_sample   a trained image whose held-out model is missing (all models saw it)

Outputs in --out-dir:
  predictions_px_<View>.csv   ID, key, view, group, image, width, height, px_per_mm,
                              session, source, cal_source, scale_bar_um, spread_px,
                              label_gap_um, procrustes_d, flags,
                              x1, y1, ... (image pixels)
  unparsed_images.txt         files whose name gives no view
  overlays/<View>/<key>.jpg   points drawn on the image (--overlays flagged|all|none)

usage: python landmark_images.py [paths ...] [--out-dir DIR] [--group GROUP] [--px-per-mm N]
  default paths: genai_lance_landmarking/raw_images (the whole mapping population)
Next: python export_geomorph.py --pred-dir DIR
"""
import argparse, csv, json, os, re, sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
CNN = REPO / "lance_landmarking" / "cnn"  # shared training/model code only
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
# Calibration, in order: --px-per-mm; the per-image calibration that Nikon NIS-Elements writes
# into its TIFFs (tag 65326, um/px; the 2560x1920 DS-Fi2-U3 images at SMZ zoom 3.00x: 1321.9
# px/mm, matching their 200 um scale bar = 264 px); else by image width. The 3840x2160 files
# carry no calibration; their 1 mm scale bar is 926-929 px, matching ImageJ's 927.
# (The ImageJ calibration of the 2560 images, 1260 px/mm, is ~5% low: it disagrees with both.)
PX_PER_MM = {3840: 927.0, 2560: 1321.9}
NIS_UM_PER_PX_TAG = 65326
NICE_BAR_UM = np.array([10, 20, 25, 50, 100, 200, 250, 500, 1000, 2000, 5000])
GROUP_DIRS = {"lbx": "LBX", "pbx": "PBX", "f1": "F1", "parents": "Parents", "non_laying_parents": "Non_Laying_Parents"}
# (view, sequence that must run proximal -> distal along the lance's axis)
ORDER = {
    "Right": [[f"R{i:02d}" for i in range(4, 11)], [f"R{i:02d}" for i in range(11, 18)]],
    "Left": [[f"L{i:02d}" for i in range(4, 11)], [f"L{i:02d}" for i in range(11, 18)]],
    "Bottom": [["B06", "B05", "B04", "B03"], ["B10", "B09", "B08", "B07"]],
}
# label_gap: 2x the median held-out error of the production models (2026-09 MCC run 36849347:
# Right 10.5, Left 10.6, Bottom 13.6 um); flags about 5% of labelled images
LABEL_GAP_UM = {"Right": 21.0, "Left": 21.0, "Bottom": 27.0}
AXIS = {"Right": ("R02", "R01"), "Left": ("L02", "L01"), "Bottom": ("B11", ("B01", "B02"))}


def find_images(paths):
    out = []
    for p in map(Path, paths):
        files = [p] if p.is_file() else sorted(q for q in p.rglob("*") if q.is_file())
        out += [f.resolve() for f in files if f.suffix.lower() in (".tif", ".tiff") and ":Zone" not in f.name]
    return out


def nis_px_per_mm(path):
    """px/mm from the calibration NIS-Elements stores in the TIFF, or None."""
    import tifffile
    with tifffile.TiffFile(str(path)) as t:
        tag = t.pages[0].tags.get(NIS_UM_PER_PX_TAG)
        return 1000.0 / tag.value if tag and isinstance(tag.value, float) and tag.value > 0 else None


def scale_bar_px(img):
    """Length (px) of the longest horizontal run of pure red: the burned-in scale bar; 0 if none."""
    red = (img[..., 0] > 180) & (img[..., 1] < 80) & (img[..., 2] < 80)
    best = 0
    for y in np.where(red.sum(1) > 50)[0]:
        xs = np.flatnonzero(red[y])
        breaks = np.flatnonzero(np.diff(xs) > 1)
        runs = np.diff(np.concatenate([[-1], breaks, [len(xs) - 1]]))
        best = max(best, int(runs.max()))
    return best


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
                "hw": torch.tensor(img.shape[:2]), "bar": scale_bar_px(img),
                "nis": nis_px_per_mm(self.rows[i]["path"]) or 0.0}


def trained_labels(view):
    """key -> v1.4 label (px) for the images that trained the production models
    (every one is in exactly one held-out fold)."""
    return {r["key"]: np.array(json.loads(r["landmarks_px_json"]))
            for r in csv.DictReader(open(HERE / "manifest_v14.csv")) if r["angle"] == view}


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


def draw_overlay(row, P, view, path, label=None):
    """Prediction on the image, cropped to the specimen. Anchors red (with IDs), computed point
    blue, semilandmarks yellow; if the image has a v1.4 label, it is drawn in cyan with a white
    line from each labelled point to its prediction."""
    from PIL import Image, ImageDraw
    img = Image.fromarray(load_rgb(str(row["path"])))
    pts = P if label is None else np.vstack([P, label])
    x0, y0 = np.maximum(pts.min(0) - 150, 0)
    x1, y1 = np.minimum(pts.max(0) + 150, [img.width, img.height])
    img = img.crop((int(x0), int(y0), int(x1), int(y1)))
    s = 1400 / max(img.size)
    img = img.resize((round(img.width * s), round(img.height * s)))
    d = ImageDraw.Draw(img)
    to = lambda q: (q - [x0, y0]) * s  # noqa: E731
    if label is not None:
        for a, b in zip(to(label), to(P)):
            d.line([tuple(a), tuple(b)], fill=(255, 255, 255), width=1)
            d.ellipse([a[0] - 4, a[1] - 4, a[0] + 4, a[1] + 4], outline=(0, 230, 255), width=2)
    for p, q in zip(SCHEMA["views"][view]["points"], to(P)):
        col = {"anchor": (255, 40, 40), "computed": (40, 140, 255)}.get(p["role"], (255, 220, 0))
        r = 4 if p["role"] != "semilandmark" else 3
        d.ellipse([q[0] - r, q[1] - r, q[0] + r, q[1] + r], outline=col, width=2)
        if p["role"] != "semilandmark":
            d.text((q[0] + 5, q[1] - 12), p["id"], fill=col)
    gap = f"  label gap {row['label_gap_um']} um (cyan = label)" if label is not None else ""
    d.text((8, 8), f"{row['key']}  {row['source']}  {row['flags'] or 'ok'}{gap}", fill=(255, 255, 0))
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path, quality=85)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("paths", nargs="*", default=[str(HERE.parent / "raw_images")])
    ap.add_argument("--out-dir", default=str(HERE / "output"))
    ap.add_argument("--runs", default=str(HERE / "runs" / "v14"), help="folder holding <view>_f<k>/best.pt")
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

    rows, unparsed = [], []
    for f in find_images(a.paths):
        m = NAME_RE.match(f.stem.strip())
        if not m:
            unparsed.append(str(f))
            continue
        key = re.sub(r"\s+", "", f.stem).lower()  # same key as the training manifest
        group = a.group or GROUP_DIRS.get(f.parent.name.lower(), f.parent.name)
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
        trained = trained_labels(view)
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
                    r["bar"], r["nis"] = int(b["bar"][j]), float(b["nis"][j])
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
            if a.px_per_mm:
                ppm, r["cal_source"] = a.px_per_mm, "argument"
            elif r["nis"]:
                ppm, r["cal_source"] = round(r["nis"], 2), "nis_tiff"
            else:
                ppm = PX_PER_MM.get(r["width"])
                r["cal_source"] = "image_width" if ppm else ""
            r["scale_bar_um"] = ""
            if ppm and r["bar"]:  # the burned-in bar must be a round length under this calibration
                bar_um = r["bar"] / ppm * 1000
                r["scale_bar_um"] = round(bar_um, 1)
                if np.min(np.abs(NICE_BAR_UM / bar_um - 1)) > 0.015:
                    f.append("scale_bar")
            elif not r["bar"]:
                f.append("no_bar")
            gap = ""
            if r["key"] in trained and ppm:  # held-out prediction vs the image's own label, mean over points
                gap = np.linalg.norm(preds[i] - trained[r["key"]], axis=1).mean() / ppm * 1000
                if gap > LABEL_GAP_UM[view]:
                    f.append("label_gap")
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
            if not ppm:
                f.append("no_scale")
            r.update(px_per_mm=ppm or "", session=f"cam{r['width']}", spread_px=round(spread[i], 2),
                     label_gap_um=round(gap, 1) if gap != "" else "",
                     flags=";".join(f), procrustes_d=round(pd[i], 5))
        cols = ["ID", "key", "view", "group", "image", "width", "height", "px_per_mm", "session", "source",
                "cal_source", "scale_bar_um", "spread_px", "label_gap_um", "procrustes_d", "flags"]
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
                    draw_overlay(r, preds[i], view, out / "overlays" / view / f"{r['key']}.jpg",
                                 trained.get(r["key"]))


if __name__ == "__main__":
    main()
