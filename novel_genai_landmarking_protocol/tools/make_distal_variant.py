"""Design variant for the lateral dorsal curve: start it at the window's proximal end.

Current design (v1.3): the dorsal curve starts at R18/L18, where the line through
the suture-1 ventral end (perpendicular to the heel-ventral junction -> apex axis)
reaches the dorsal edge. That start lies next to the heel, where the golden basal
flap often sits, and the curve's evenly spaced semilandmarks all hang from it.

Variant ("distal"): the same construction through R11/L11 (window proximal end)
instead of R04/L04, i.e. further from the heel. Point count and IDs are unchanged
(R18/L18 = the new start, 10 dorsal semilandmarks resampled from there to the apex),
so the schema and sliders are shared. The new start lies on the already-traced
dorsal edge, so the variant is computed from the v1.3 labels: the dorsal polyline
R18 -> dorsal1..10 -> R01 is cut at the new start and resampled.

writes autolabels/labels_<View>_distal.csv for Right and Left.
"""
import csv, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from autolabel import point_order  # noqa: E402

AL = os.path.join(HERE, "..", "autolabels")


def resample(poly, k):
    s = np.r_[0, np.cumsum(np.linalg.norm(np.diff(poly, axis=0), axis=1))]
    t = np.linspace(0, s[-1], k + 2)
    return np.c_[np.interp(t, s, poly[:, 0]), np.interp(t, s, poly[:, 1])]


for view in ("Right", "Left"):
    s = view[0]
    ids = point_order(view)
    rows = list(csv.DictReader(open(os.path.join(AL, f"labels_{view}.csv"))))
    out, missing = [], []
    for r in rows:
        P = {i: np.array([float(r[f"{i}_x"]), float(r[f"{i}_y"])]) for i in ids}
        ax = (P[f"{s}01"] - P[f"{s}02"]) / np.linalg.norm(P[f"{s}01"] - P[f"{s}02"])
        poly = np.array([P[f"{s}18"]] + [P[f"{s}.dorsal{k}"] for k in range(1, 11)] + [P[f"{s}01"]])
        along = (poly - P[f"{s}11"]) @ ax  # position along the lance axis relative to the window's proximal end
        cross = np.flatnonzero((along[:-1] < 0) & (along[1:] >= 0))
        if not len(cross):
            missing.append(r["key"])
            continue
        i = cross[0]
        f = -along[i] / (along[i + 1] - along[i])
        start = poly[i] + f * (poly[i + 1] - poly[i])
        new = resample(np.vstack([start, poly[i + 1:]]), 10)  # start, 10 interior, apex
        P[f"{s}18"] = new[0]
        for k in range(1, 11):
            P[f"{s}.dorsal{k}"] = new[k]
        r2 = dict(r)
        for pid in [f"{s}18"] + [f"{s}.dorsal{k}" for k in range(1, 11)]:
            r2[f"{pid}_x"], r2[f"{pid}_y"] = f"{P[pid][0]:.2f}", f"{P[pid][1]:.2f}"
        out.append(r2)
    with open(os.path.join(AL, f"labels_{view}_distal.csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, list(rows[0]))
        w.writeheader()
        w.writerows(out)
    print(f"{view}: {len(out)} labels; window start not on the traced dorsal edge in {len(missing)}: {missing[:5]}")
