"""Convert a digitizer's ImageJ ROI set into the protocol's landmark configuration.

A digitizer produces, per image, one ImageJ ROI Manager set (`SampleID_<V>_ROI.zip`):
  1. "anchors": one Multi-point ROI with the view's anchors clicked in order
     (Right R01-R17, Left L01-L17, Bottom B01-B13);
  2. one Segmented Line ROI per traced curve, in the order listed in CURVES.
This script trims each trace at its anchors, computes the Type III points
(R18/L18 dorsal curve start, B14 fork crotch) and resamples the semilandmarks
at equal arc length, giving the full configuration (Right 42, Left 40,
Bottom 38 points) with the same point IDs as landmark_schema.json.

usage:
  python roi_to_landmarks.py <view> <roi.zip> [...]      -> prints QC, writes <roi>_landmarks.csv
  python roi_to_landmarks.py --table out.csv <files...>  -> also one wide table (one row per image)
view = Right | Left | Bottom, or "auto" to take it from the file name (_R_, _L_, _B_).
"""
import argparse, csv, os, re, sys
import numpy as np
import roifile

# Curves as the digitizer traces them: (name, start anchor, end anchor, n semilandmarks).
# None as start means "start anywhere proximal to the computed point" (dorsal
# curve), "fork" is one trace from B01 round the bottom of the gap to B02.
CURVES = {
    "Right": [("R.heel", "R03", "R02", 4), ("R.vbase", "R02", "R04", 2), ("R.vdist", "R10", "R01", 4),
              ("R.dorsal", None, "R01", 10), ("R.window", "R11", "R17", 4)],
    "Left": [("L.heel", "L03", "L02", 4), ("L.vbase", "L02", "L04", 2), ("L.vdist", "L10", "L01", 2),
             ("L.dorsal", None, "L01", 10), ("L.window", "L11", "L17", 4)],
    "Bottom": [("B.fork", "B01", "B02", 3), ("B.outL", "B03", "B01", 3), ("B.outS", "B07", "B02", 3),
               ("B.sideL", "B06", "B12", 6), ("B.sideS", "B10", "B13", 6)],
}
N_ANCHORS = {"Right": 17, "Left": 17, "Bottom": 13}
PREFIX = {"Right": "R", "Left": "L", "Bottom": "B"}
END_TOL_PX = 25  # a trace end further than this from its anchor is reported


def densify(poly, step=1.0):
    s = np.r_[0, np.cumsum(np.linalg.norm(np.diff(poly, axis=0), axis=1))]
    t = np.arange(0, s[-1], step)
    t = np.r_[t, s[-1]]
    return np.c_[np.interp(t, s, poly[:, 0]), np.interp(t, s, poly[:, 1])]


def resample(poly, k):
    """k interior points at equal arc length along poly (ends excluded)."""
    s = np.r_[0, np.cumsum(np.linalg.norm(np.diff(poly, axis=0), axis=1))]
    t = np.linspace(0, s[-1], k + 2)[1:-1]
    return np.c_[np.interp(t, s, poly[:, 0]), np.interp(t, s, poly[:, 1])]


def between(trace, a, b):
    """Part of the trace between the points nearest a and b, oriented a -> b, ends set to a and b."""
    i = int(np.argmin(np.linalg.norm(trace - a, axis=1)))
    j = int(np.argmin(np.linalg.norm(trace - b, axis=1)))
    seg = trace[i:j + 1] if i <= j else trace[j:i + 1][::-1]
    return np.vstack([a, seg[1:-1], b]) if len(seg) > 2 else np.vstack([a, b])


def read_set(path):
    rois = roifile.roiread(path)
    rois = rois if isinstance(rois, list) else [rois]
    out = []
    for r in rois:
        xy = r.coordinates()
        if xy is None:
            xy = r.subpixel_coordinates
        out.append((r.name or "", int(r.roitype), np.asarray(xy, float)))
    return out


def convert(view, path):
    msgs, P, kinds = [], {}, {}
    rois = read_set(path)
    points = [r for r in rois if r[1] == roifile.ROI_TYPE.POINT]
    lines = [r for r in rois if r[1] != roifile.ROI_TYPE.POINT]
    if len(points) != 1:
        raise ValueError(f"expected exactly 1 multi-point ROI (the anchors), found {len(points)}")
    anchors = points[0][2]
    n = N_ANCHORS[view]
    if len(anchors) != n:
        raise ValueError(f"{view}: expected {n} anchors, found {len(anchors)}")
    for i, p in enumerate(anchors):
        P[f"{PREFIX[view]}{i + 1:02d}"] = p
        kinds[f"{PREFIX[view]}{i + 1:02d}"] = "anchor"
    spec = CURVES[view]
    if len(lines) != len(spec):
        raise ValueError(f"{view}: expected {len(spec)} traced curves, found {len(lines)}")
    # match curves by name when the digitizer named them, otherwise by order
    byname = {nm: xy for nm, _, xy in lines}
    traces = {}
    for k, (name, *_ ) in enumerate(spec):
        if name in byname:
            traces[name] = byname[name]
        else:
            traces[name] = lines[k][2]
            if lines[k][0]:
                msgs.append(f"curve {k + 1} named '{lines[k][0]}', expected '{name}': used by position")
    semis = {}
    for name, a, b, k in spec:
        tr = densify(traces[name])
        for end, lab in ((a, "start"), (b, "end")):
            if end is not None:
                d = np.linalg.norm(tr - P[end], axis=1).min()
                if d > END_TOL_PX:
                    msgs.append(f"{name}: {lab} anchor {end} is {d:.0f} px from the trace")
        if name.endswith(".dorsal"):
            s = PREFIX[view]
            ax = (P[f"{s}01"] - P[f"{s}02"]) / np.linalg.norm(P[f"{s}01"] - P[f"{s}02"])
            along = (tr - P[f"{s}04"]) @ ax
            cross = np.flatnonzero(np.diff(np.sign(along)) != 0)
            if not len(cross):
                raise ValueError(f"{name}: trace does not reach back past suture 1 (start it further proximally)")
            i = cross[0]
            f = along[i] / (along[i] - along[i + 1])
            start = tr[i] + f * (tr[i + 1] - tr[i])
            comp = f"{s}18"
            P[comp], kinds[comp] = start, "computed"
            poly = between(tr, start, P[b])
            semis[name] = resample(poly, k)
        elif name == "B.fork":
            tip = (P["B01"] + P["B02"]) / 2
            ax = (tip - P["B11"]) / np.linalg.norm(tip - P["B11"])
            poly = between(tr, P["B01"], P["B02"])
            crotch = poly[int(np.argmin((poly - P["B11"]) @ ax))]
            P["B14"], kinds["B14"] = crotch, "computed"
            semis["B.medL"] = resample(between(poly, crotch, P["B01"]), k)
            semis["B.medS"] = resample(between(poly, crotch, P["B02"]), k)
        elif name.endswith(".window"):
            s = PREFIX[view]
            tops = [P[f"{s}{i:02d}"] for i in range(12, 17)]
            poly = between(tr, P[a], P[b])
            semis[name] = np.array([resample(between(poly, tops[i], tops[i + 1]), 1)[0] for i in range(4)])
        else:
            semis[name] = resample(between(tr, P[a], P[b]), k)
    # QC: sutures must run in order along the margin
    s = PREFIX[view]
    if view in ("Right", "Left"):
        ax = P[f"{s}01"] - P[f"{s}02"]
        ids = [f"{s}{i:02d}" for i in range(4, 11 if view == "Right" else 10)]
        t = [(P[i] - P[f"{s}02"]) @ ax for i in ids]
        if any(np.diff(t) <= 0):
            msgs.append("suture ventral ends are not in heel-to-apex order: check click order")
    else:
        for ids in (["B03", "B04", "B05", "B06"], ["B07", "B08", "B09", "B10"]):
            ax = (P["B01"] + P["B02"]) / 2 - P["B11"]
            t = [(P[i] - P["B11"]) @ ax for i in ids]
            if any(np.diff(t) >= 0):
                msgs.append(f"{ids[0]}-{ids[-1]} are not in apex-to-base order: check click order")
    order = list(P)
    rows = [(pid, kinds[pid], *P[pid]) for pid in order]
    curve_order = [c[0] for c in spec if c[0] != "B.fork"]
    if view == "Bottom":
        curve_order = ["B.medL", "B.medS"] + curve_order
    for c in curve_order:
        for i, p in enumerate(semis[c]):
            rows.append((f"{c}{i + 1}", "semilandmark", *p))
    return rows, msgs


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("view", nargs="?", default="auto")
    ap.add_argument("files", nargs="+")
    ap.add_argument("--table", help="also write one wide CSV, one row per image")
    a = ap.parse_args()
    wide, header, bad = [], None, 0
    for f in a.files:
        view = a.view
        if view == "auto":
            m = re.search(r"_([RLB])(?:\d+)?_ROI", os.path.basename(f), re.I)
            if not m:
                print(f"{f}: can't tell the view from the name; pass Right/Left/Bottom", file=sys.stderr)
                bad += 1
                continue
            view = {"R": "Right", "L": "Left", "B": "Bottom"}[m.group(1).upper()]
        try:
            rows, msgs = convert(view, f)
        except ValueError as e:
            print(f"FAIL {f}: {e}")
            bad += 1
            continue
        out = re.sub(r"\.zip$", "", f) + "_landmarks.csv"
        with open(out, "w", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["point", "kind", "x_px", "y_px"])
            w.writerows(rows)
        print(("WARN " if msgs else "OK   ") + f"{f} -> {out} ({len(rows)} points)")
        for m in msgs:
            print("       " + m)
        hdr = ["file", "view"] + [c for r in rows for c in (r[0] + "_x", r[0] + "_y")]
        header = header or {}
        header.setdefault(view, hdr)
        wide.append((view, [f, view] + [v for r in rows for v in r[2:]]))
    if a.table and wide:
        with open(a.table, "w", newline="") as fh:
            w = csv.writer(fh)
            for view in sorted(set(v for v, _ in wide)):
                w.writerow(header[view])
                w.writerows(r for v, r in wide if v == view)
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
