"""Automatic new-protocol labels for every image that has an old-protocol digitization.

Per image (manifest row with a complete old digitization):
  * old suture points are put back in anatomical order if they were clicked out
    of order (2 of 958 images in the current data);
  * the full new configuration is built exactly as for the figures
    (draw_protocol.build): old points -> anchors, automatic sclerite outline ->
    outline curves, old points -> interior curves, geometric rules -> B11-B13 and
    the computed points. No hand corrections are used.
  * QC: the old human points that lie on the outline (suture ends, dorsal-edge
    points, apices, heel points) are an independent check of the automatic
    outline. Their distance to it, and the curve lengths, decide pass/fail.

Writes, under genai_lance_landmarking/autolabels/:
  labels_<View>.csv  one row per image: key, group, raw_image, then <id>_x, <id>_y (full-res px)
  qc.csv             one row per image and view: status, reason, outline-check distances

usage: python autolabel.py [--workers 4] [--views Right Left Bottom] [--limit N]
"""
import argparse, csv, json, os, sys, traceback
from multiprocessing import Pool
import numpy as np
import tifffile

sys.path.insert(0, os.path.dirname(__file__))
import draw_protocol as dp  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "autolabels")
SCHEMA = json.load(open(os.path.join(HERE, "..", "landmark_schema.json")))

# old-protocol points (1-indexed) that a digitizer placed on the outer outline
ON_OUTLINE = {
    "Right": [1, 2, 3, *range(4, 11), 11, 12, 13, 28, *range(30, 37)],
    "Left": [1, 2, 3, *range(4, 11), *range(26, 33)],
    "Bottom": [1, 13, 2, 3, 4, 5, 14, 15, 16, 17],
}


def fix_order(view, old):
    """Put old suture points back in anatomical order (they must be ordered along the lance)."""
    old = old.copy()
    if view in ("Right", "Left"):
        idx = list(range(3, 10 if view == "Right" else 9))
        ax = old[12] - old[2]
        t = (old[idx] - old[2]) @ ax
        old[idx] = old[idx][np.argsort(t)]
    else:
        base = (old[4] + old[16]) / 2
        ax = (old[0] + old[12]) / 2 - base
        for idx in ([1, 2, 3, 4], [13, 14, 15, 16]):
            t = (old[idx] - base) @ ax
            old[idx] = old[idx][np.argsort(-t)]
    return old


def point_order(view):
    return [p["id"] for p in SCHEMA["views"][view]["points"]]


def one(row):
    view, key = row["angle"], row["key"]
    rec = dict(key=key, group=row["group"], view=view, raw_image=row["raw_image"])
    try:
        img = tifffile.imread(dp.LANCE + row["raw_image"])[..., :3]
        old0 = np.array(json.loads(row["landmarks_px_json"]), float)
        old = fix_order(view, old0)
        rec["reordered"] = int(not np.allclose(old, old0))
        try:
            C, P, kind, curves = dp.build(view, img, old, key="")
        except ValueError as e:  # shoulder rule declined: foreign structure merged into outline
            rec.update(status="fail", reason=f"shoulder: {e}".split(":")[0] + ": " + str(e)[:60])
            return rec, None
        # outline check against the old human on-outline points
        d = np.array([np.linalg.norm(C - old[i - 1], axis=1).min() for i in ON_OUTLINE[view]])
        per = np.sum(np.linalg.norm(np.diff(C, axis=0), axis=1))
        rec.update(check_median=round(float(np.median(d)), 1), check_p90=round(float(np.percentile(d, 90)), 1),
                   check_max=round(float(d.max()), 1), perimeter=round(float(per), 0))
        for name, poly, _ in curves:
            rec[f"len_{name}"] = round(float(np.sum(np.linalg.norm(np.diff(poly, axis=0), axis=1))), 1)
        ids = point_order(view)
        missing = [i for i in ids if i not in P]
        if missing:
            rec.update(status="fail", reason=f"missing {missing[:3]}")
            return rec, None
        rec["status"] = "ok"  # provisional; thresholds applied after the whole run
        return rec, [key, row["group"], row["raw_image"]] + [float(v) for i in ids for v in P[i]]
    except Exception as e:
        rec.update(status="fail", reason=f"error: {type(e).__name__}: {str(e)[:80]}")
        traceback.print_exc()
        return rec, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--views", nargs="+", default=["Right", "Left", "Bottom"])
    ap.add_argument("--limit", type=int)
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    rows = [r for r in csv.DictReader(open(dp.LANCE + "manifest.csv"))
            if r["angle"] in a.views and r["landmarks_px_json"] and r["n_found"] == r["n_expected"]
            and r["raw_image"] and os.path.exists(dp.LANCE + r["raw_image"])]
    if a.limit:
        rows = rows[: a.limit]
    print(f"{len(rows)} images", flush=True)
    recs, labels = [], {v: [] for v in a.views}
    with Pool(a.workers) as pool:
        for k, (rec, lab) in enumerate(pool.imap_unordered(one, rows, chunksize=2)):
            recs.append(rec)
            if lab:
                labels[rec["view"]].append(lab)
            if (k + 1) % 25 == 0:
                print(f"{k + 1}/{len(rows)}", flush=True)
    for v in a.views:
        with open(os.path.join(OUT, f"labels_{v}.csv"), "w", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["key", "group", "raw_image"] + [f"{i}_{c}" for i in point_order(v) for c in "xy"])
            w.writerows(sorted(labels[v]))
    cols = sorted({k for r in recs for k in r}, key=lambda c: (not c in ("key", "group", "view", "status", "reason"), c))
    with open(os.path.join(OUT, "qc.csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, cols)
        w.writeheader()
        w.writerows(sorted(recs, key=lambda r: (r["view"], r["key"])))
    print("done", flush=True)


if __name__ == "__main__":
    main()
