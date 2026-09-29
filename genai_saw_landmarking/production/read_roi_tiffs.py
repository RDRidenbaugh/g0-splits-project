"""Read landmarks corrected in Fiji back from the TIFFs of write_roi_tiffs.py.

Workflow: python write_roi_tiffs.py -> open output/roi_tiffs/<key>.tif in Fiji -> drag the wrong points with
the Multi-point tool (never add or delete one) -> File > Save (keeps the multi-point selection in the TIFF)
-> python read_roi_tiffs.py -> python export_geomorph.py.

For each TIFF (default: every .tif in output/roi_tiffs/), reads the active multi-point ROI (or, if the
selection was lost, <key>.roi saved next to it from the ROI Manager), checks it has the 52 points and that
the image matches the predictions, and compares it with the CNN prediction in predictions_px_saw.csv.
Coordinates are in the protocol frame, the same pixel grid as the predictions.

Writes fiji_corrections.csv (this folder, kept like qc_review.csv; one row per key, a re-read replaces the
row): key, n_moved, max_move_um, moved (point IDs), cnn_source, file, read_on, x1, y1, ... x52, y52.
export_geomorph.py uses these coordinates instead of the CNN's and passes the image's QC unless
qc_review.csv says drop. Unchanged files (no point moved) are reported and not written, unless --keep-unchanged.

usage: python read_roi_tiffs.py [files or folders ...] [--keep-unchanged] [--dry-run]
"""
import argparse, csv, datetime, re, sys
from pathlib import Path

import numpy as np
import roifile
import tifffile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "tools"))
import scheme  # noqa: E402

ORDER = [p for p, _ in scheme.point_order()]
N = len(ORDER)
MOVED_PX = 0.05  # float32 round trip is exact to ~1e-4 px; anything larger was moved in Fiji
CORR = HERE / "fiji_corrections.csv"
HEAD = ["key", "n_moved", "max_move_um", "moved", "cnn_source", "file", "read_on"] + \
       [f"{c}{k}" for k in range(1, N + 1) for c in "xy"]


def read_points(tif):
    """(key, (N, 2) points, image height, width) from a TIFF written by write_roi_tiffs.py and saved by Fiji."""
    with tifffile.TiffFile(str(tif)) as t:
        md = t.imagej_metadata or {}
        s = t.series[0]
        h, w = s.shape[s.axes.index("Y")], s.shape[s.axes.index("X")]
    m = re.search(r"^key = (\S+)", md.get("Info", ""), re.M)
    key = m.group(1) if m else tif.stem
    if md.get("ROI"):
        roi = roifile.ImagejRoi.frombytes(md["ROI"])
    elif tif.with_suffix(".roi").exists():
        roi = roifile.ImagejRoi.fromfile(str(tif.with_suffix(".roi")))
    else:
        raise ValueError("no selection saved in the TIFF and no .roi next to it "
                         "(select the points again: Edit > Selection > Restore Selection, then save)")
    if roi.roitype != roifile.ROI_TYPE.POINT:
        raise ValueError(f"the saved selection is a {roi.roitype.name}, not the multi-point ROI")
    return key, np.asarray(roi.coordinates(), float), h, w


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("paths", nargs="*", default=[str(HERE / "output" / "roi_tiffs")])
    ap.add_argument("--pred", default=str(HERE / "output" / "predictions_px_saw.csv"))
    ap.add_argument("--keep-unchanged", action="store_true", help="also record files where no point moved")
    ap.add_argument("--dry-run", action="store_true", help="report only; do not write fiji_corrections.csv")
    a = ap.parse_args()

    pred = {r["key"]: r for r in csv.DictReader(open(a.pred))}
    old = {r["key"]: r for r in csv.DictReader(open(CORR))} if CORR.exists() else {}
    files = []
    for p in map(Path, a.paths):
        files += sorted(p.glob("*.tif")) if p.is_dir() else [p]
    new, bad = {}, 0
    today = datetime.date.today().isoformat()
    for f in files:
        try:
            key, P, h, w = read_points(f)
            if key not in pred:
                raise ValueError(f"key {key} is not in {Path(a.pred).name}")
            r = pred[key]
            if (h, w) != (int(r["height"]), int(r["width"])):
                raise ValueError(f"image is {w}x{h}, predictions are for {r['width']}x{r['height']} (cropped or resized?)")
            if len(P) != N:
                raise ValueError(f"{len(P)} points, expected {N} (points were added or deleted: re-export this image)")
        except ValueError as e:
            print(f"FAIL {f.name}: {e}")
            bad += 1
            continue
        cnn = np.array([[float(r[f"x{k}"]), float(r[f"y{k}"])] for k in range(1, N + 1)])
        d = np.linalg.norm(P - cnn, axis=1)
        moved = [ORDER[i] for i in np.flatnonzero(d > MOVED_PX)]
        ppm = float(r["px_per_mm"]) if r["px_per_mm"] else np.nan
        max_um = round(float(d.max()) / ppm * 1000, 1) if ppm == ppm else ""
        print(f"{'OK  ' if moved else 'same'} {key}: {len(moved)} moved" + (f", max {max_um} um: {' '.join(moved)}" if moved else ""))
        if moved or a.keep_unchanged:
            new[key] = dict(key=key, n_moved=len(moved), max_move_um=max_um, moved=" ".join(moved), cnn_source=r["source"],
                            file=str(f.relative_to(HERE)) if f.is_relative_to(HERE) else str(f), read_on=today,
                            **{f"{c}{k}": round(float(P[k - 1, j]), 2) for k in range(1, N + 1) for j, c in enumerate("xy")})
    print(f"{len(files)} files: {len(new)} to record, {bad} failed")
    if new and not a.dry_run:
        old.update(new)
        with open(CORR, "w", newline="") as fh:
            wr = csv.DictWriter(fh, fieldnames=HEAD)
            wr.writeheader()
            wr.writerows(old[k] for k in sorted(old))
        print(f"-> {CORR.name} ({len(old)} corrected images); next: python export_geomorph.py")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
