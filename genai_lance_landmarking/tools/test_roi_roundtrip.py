"""Round-trip check for roi_to_landmarks.py.

For each figure specimen and view, builds the ImageJ ROI set a digitizer would
save (anchors clicked in order + one traced polyline per curve, taken from the
segmented outline), converts it, and compares every point with the figure's
own geometry (draw_protocol.build). Window semilandmarks are excluded from the
comparison: the figures place them at the old protocol's crest points, the
converter at arc-length midpoints between suture ends (they slide in GPA).

usage: python test_roi_roundtrip.py [outdir]
"""
import os, sys, tempfile
import numpy as np
import roifile
sys.path.insert(0, os.path.dirname(__file__))
import draw_protocol as dp  # noqa: E402
from roi_to_landmarks import convert, CURVES  # noqa: E402

KEYS = ["ll280xll284-1", "px014xnp060v4-2", "feb1xpbx012-1-v35"]


def poly_roi(xy, name, kind):
    r = roifile.ImagejRoi.frompoints(np.asarray(xy, float), name=name)
    r.roitype = kind
    return r


def human_traces(view, C, P, curves):
    near = lambda p: int(np.argmin(np.linalg.norm(C - p, axis=1)))
    arc = lambda a, b, avoid: C[dp.arc_indices(len(C), near(P[a]), near(P[b]), near(P[avoid]))]
    got = {name: poly for name, poly, _ in curves}
    s = view[0]
    out = []
    for name, a, b, _ in CURVES[view]:
        if name.endswith(".dorsal"):  # digitizer starts at the top of the heel
            tr = arc(f"{s}03", b, f"{s}02")
        elif name == "B.fork":
            tr = arc("B01", "B02", "B04")
        elif name.endswith(".window") or name == "L.vdist":
            tr = got[name]
        else:
            tr = arc(a, b, "B14" if name.startswith("B.out") else (f"{s}01" if name.startswith("B.side") else
                     (f"{s}02" if name.endswith("vdist") else f"{s}01")))
        out.append((name, tr))
    return out


def main():
    outdir = sys.argv[1] if len(sys.argv) > 1 else tempfile.mkdtemp()
    worst = 0.0
    for key in KEYS:
        for view in ("Right", "Left", "Bottom"):
            img, old = dp.load(key, view)
            C, P, kind, curves = dp.build(view, img, old, key)
            anchors = [P[k] for k in P if kind[k] == "anchor"]
            rois = [poly_roi(anchors, "anchors", roifile.ROI_TYPE.POINT)]
            rois += [poly_roi(tr, name, roifile.ROI_TYPE.POLYLINE)
                     for name, tr in human_traces(view, C, P, curves)]
            path = os.path.join(outdir, f"{key}_{view[0]}_ROI.zip")
            if os.path.exists(path):
                os.remove(path)
            roifile.roiwrite(path, rois)
            rows, msgs = convert(view, path)
            got = {r[0]: np.array(r[2:], float) for r in rows}
            d = {k: np.linalg.norm(got[k] - P[k]) for k in got if k in P and ".window" not in k}
            missing = [k for k in P if k not in got]
            m = max(d.values())
            worst = max(worst, m)
            print(f"{key:18s} {view:6s} points {len(rows):3d}  max diff {m:5.1f}px  "
                  f"median {np.median(list(d.values())):4.1f}px  "
                  f"worst {max(d, key=d.get)}  missing {missing}  msgs {msgs}")
    print(f"worst difference overall: {worst:.1f} px")


if __name__ == "__main__":
    main()
