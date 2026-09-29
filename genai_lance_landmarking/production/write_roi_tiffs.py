"""Write the CNN landmarks into ImageJ TIFFs for review in Fiji (optional step after landmark_images.py).

For each selected image, writes output/roi_tiffs/<View>/<key>.tif:
  * the raw image, unchanged (predictions_px_<View>.csv is in raw-image pixels);
  * the view's predicted points (Right 42, Left 40, Bottom 38) as ONE multi-point ROI (the image's active
    selection), in landmark_schema.json order. To correct a point, drag it with the Multi-point tool.
    Do not add or delete points: the order is the identity;
  * an overlay naming every anchor and computed point at its CNN position (anchors red, computed blue)
    and marking the semilandmarks (yellow), so a moved point can be compared with where the CNN put it
    (Image > Overlay > Hide Overlay to hide it);
  * the image's own calibration (px_per_mm from the predictions), so Fiji measures in microns;
  * Image > Show Info: ID, key, view, CNN source, QC flags, label gap and the point order.
Coordinates are written unchanged (continuous pixels, origin at the image's top-left corner).

usage: python write_roi_tiffs.py                    # flagged images only (as the overlays)
       python write_roi_tiffs.py --all [--views Right,Left]
       python write_roi_tiffs.py --keys ll280xll284-1_r px014xnp060v4-2_b [--out-dir DIR]
"""
import argparse, csv, json, sys
from pathlib import Path

import numpy as np
import roifile
import tifffile

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
SCHEMA = json.load(open(HERE.parent / "landmark_schema.json"))
COLOR = {"anchor": b"\xff\xff\x28\x28", "computed": b"\xff\x28\x8c\xff", "semilandmark": b"\xff\xff\xdc\x00"}  # ARGB


def load_rgb(f):
    """RGB uint8 (H, W, 3) from a .tif (RGB, CYX composite or grey)."""
    with tifffile.TiffFile(str(f)) as t:
        a, ax = t.series[0].asarray(), t.series[0].axes
    if a.ndim == 3 and ax.startswith("C"):
        a = np.moveaxis(a, 0, -1)
    if a.ndim == 2:
        a = np.stack([a] * 3, -1)
    return np.ascontiguousarray(a[..., :3]).astype(np.uint8)


def point_roi(xy, name, color=None, names=False):
    r = roifile.ImagejRoi.frompoints(np.asarray(xy, float).reshape(-1, 2), name=name)
    r.roitype = roifile.ROI_TYPE.POINT
    if color:
        r.stroke_color = color
    if names:
        r.options |= roifile.ROI_OPTIONS.OVERLAY_NAMES
    return r


def write(path, img, P, points, ppm, info):
    roi = point_roi(P, "cnn")
    named = [q["role"] in ("anchor", "computed") for q in points]
    overlays = [point_roi(p, q["id"], COLOR[q["role"]], names=True) for q, p, k in zip(points, P, named) if k]
    overlays.append(point_roi([p for p, k in zip(P, named) if not k], "semilandmarks", COLOR["semilandmark"]))
    meta = {"ROI": roi.tobytes(), "Overlays": [o.tobytes() for o in overlays], "Info": info}
    kw = {}
    if ppm:
        meta["unit"] = "micron"
        kw["resolution"] = (ppm / 1000.0, ppm / 1000.0)  # pixels per micron
    path.parent.mkdir(parents=True, exist_ok=True)
    tifffile.imwrite(path, img, imagej=True, metadata=meta, compression="zlib", **kw)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--pred-dir", default=str(HERE / "output"), help="folder holding predictions_px_<View>.csv")
    ap.add_argument("--out-dir", default=str(HERE / "output" / "roi_tiffs"))
    ap.add_argument("--views", default="Right,Left,Bottom")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--all", action="store_true", help="every image (default: flagged images only)")
    g.add_argument("--keys", nargs="+", help="these image keys only")
    a = ap.parse_args()

    found = set()
    for view in a.views.split(","):
        pred = Path(a.pred_dir) / f"predictions_px_{view}.csv"
        if not pred.exists():
            print(f"{view}: no {pred} -- skipped")
            continue
        rows = list(csv.DictReader(open(pred)))
        if a.keys:
            rows = [r for r in rows if r["key"] in a.keys]
        elif not a.all:
            rows = [r for r in rows if r["flags"]]
        points = SCHEMA["views"][view]["points"]
        n = len(points)
        for r in rows:
            found.add(r["key"])
            P = np.array([[float(r[f"x{k}"]), float(r[f"y{k}"])] for k in range(1, n + 1)])
            img = load_rgb(REPO / r["image"])
            if img.shape[:2] != (int(r["height"]), int(r["width"])):
                sys.exit(f"{r['key']}: image is {img.shape[1]}x{img.shape[0]}, predictions are for "
                         f"{r['width']}x{r['height']}")
            info = "\n".join([
                f"ID = {r['ID']}", f"key = {r['key']}", f"view = {view}", f"group = {r['group']}",
                f"image = {r['image']}", f"source = {r['source']}", f"flags = {r['flags'] or 'ok'}",
                f"label_gap_um = {r['label_gap_um']}", f"px_per_mm = {r['px_per_mm']} ({r['cal_source']})",
                "points (multi-point ROI order) = " + ",".join(q["id"] for q in points)])
            write(Path(a.out_dir) / view / f"{r['key']}.tif", img, P, points,
                  float(r["px_per_mm"]) if r["px_per_mm"] else None, info)
        print(f"{view}: {len(rows)} TIFFs with {n}-point ROIs -> {Path(a.out_dir) / view}")
    if a.keys and set(a.keys) - found:
        print(f"not found in the predictions: {sorted(set(a.keys) - found)}", file=sys.stderr)


if __name__ == "__main__":
    main()
