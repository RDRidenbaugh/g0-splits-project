"""Write the CNN landmarks into ImageJ TIFFs for review in Fiji (optional step after landmark_images.py).

For each selected image, writes output/roi_tiffs/<key>.tif:
  * the raw image in the PROTOCOL frame (apex left, teeth up; ../tools/frame.py): mirrored if the row says
    mirrored, then flipped top to bottom. This is the same pixel grid as predictions_px_saw.csv, so the
    points need no transformation. True colours by default; --prepared uses the colour-normalized CNN input
    (images/<key>.tif) instead;
  * the 52 predicted points as ONE multi-point ROI (the image's active selection) in point_order():
    anchors first (S01, V1-V7, T2-T4, R1-R7, D1-D7), then the ventral and rachis semilandmarks. To correct
    a point, drag it with the Multi-point tool. Do not add or delete points: the order is the identity;
  * an overlay naming every anchor at its CNN position (red) and marking the semilandmarks (yellow), so a
    moved point can be compared with where the CNN put it (Image > Overlay > Hide Overlay to hide it);
  * the image's own calibration (px_per_mm from image_table.csv), so Fiji measures in microns;
  * Image > Show Info: key, CNN source, QC flags, label gap and the point order.
Coordinates are written unchanged (continuous pixels, origin at the image's top-left corner).

usage: python write_roi_tiffs.py                    # flagged images only (as the overlays)
       python write_roi_tiffs.py --all
       python write_roi_tiffs.py --keys rb029_f1_r ag078_f3_r [--prepared] [--out-dir DIR]
"""
import argparse, csv, sys
from pathlib import Path

import numpy as np
import roifile
import tifffile
from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "tools"))
import scheme  # noqa: E402
from frame import image_to_protocol  # noqa: E402

ORDER = scheme.point_order()
RED, YELLOW = b"\xff\xff\x28\x28", b"\xff\xff\xdc\x00"  # ARGB


def load_rgb(f):
    """RGB uint8 (H, W, 3) from a .tif (RGB, CYX composite or grey) or .jpg."""
    f = str(f)
    if f.lower().endswith(".jpg"):
        return np.array(Image.open(f).convert("RGB"))
    with tifffile.TiffFile(f) as t:
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


def write(path, img, P, ppm, info):
    roi = point_roi(P, "cnn")
    overlays = [point_roi(p, pid, RED, names=True) for (pid, role), p in zip(ORDER, P) if role != "semi"]
    overlays.append(point_roi([p for (_, role), p in zip(ORDER, P) if role == "semi"], "semilandmarks", YELLOW))
    meta = {"ROI": roi.tobytes(), "Overlays": [o.tobytes() for o in overlays], "Info": info}
    kw = {}
    if ppm:
        meta["unit"] = "micron"
        kw["resolution"] = (ppm / 1000.0, ppm / 1000.0)  # pixels per micron
    path.parent.mkdir(parents=True, exist_ok=True)
    tifffile.imwrite(path, img, imagej=True, metadata=meta, compression="zlib", **kw)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--pred", default=str(HERE / "output" / "predictions_px_saw.csv"))
    ap.add_argument("--out-dir", default=str(HERE / "output" / "roi_tiffs"))
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--all", action="store_true", help="every image (default: flagged images only)")
    g.add_argument("--keys", nargs="+", help="these image keys only")
    ap.add_argument("--prepared", action="store_true", help="use the colour-normalized CNN image, not the raw one")
    a = ap.parse_args()

    rows = list(csv.DictReader(open(a.pred)))
    if a.keys:
        missing = set(a.keys) - {r["key"] for r in rows}
        if missing:
            sys.exit(f"not in {a.pred}: {sorted(missing)}")
        rows = [r for r in rows if r["key"] in a.keys]
    elif not a.all:
        rows = [r for r in rows if r["flags"]]
    n = len(ORDER)
    out = Path(a.out_dir)
    for r in rows:
        P = np.array([[float(r[f"x{k}"]), float(r[f"y{k}"])] for k in range(1, n + 1)])
        if a.prepared:
            img = load_rgb(HERE / r["image"])
        else:
            img = load_rgb(HERE / r["raw_image"])
            if int(r["mirrored"]):
                img = img[:, ::-1]
            if int(r["vflipped"]):
                img = image_to_protocol(img)
        if img.shape[:2] != (int(r["height"]), int(r["width"])):
            sys.exit(f"{r['key']}: image is {img.shape[1]}x{img.shape[0]}, predictions are for "
                     f"{r['width']}x{r['height']}")
        info = "\n".join([
            f"key = {r['key']}", f"id = {r['id']}", f"side = {r['side']}",
            f"image = {'prepared ' + r['image'] if a.prepared else 'raw ' + r['raw_image']} "
            f"(protocol frame: apex left, teeth up; mirrored={r['mirrored']}, vflipped={r['vflipped']})",
            f"source = {r['source']}", f"flags = {r['flags'] or 'ok'}", f"label_gap_um = {r['label_gap_um']}",
            f"px_per_mm = {r['px_per_mm']} ({r['cal_source']})",
            "points (multi-point ROI order) = " + ",".join(pid for pid, _ in ORDER)])
        write(out / f"{r['key']}.tif", np.ascontiguousarray(img), P,
              float(r["px_per_mm"]) if r["px_per_mm"] else None, info)
    print(f"{len(rows)} TIFFs with {n}-point ROIs -> {out}")


if __name__ == "__main__":
    main()
