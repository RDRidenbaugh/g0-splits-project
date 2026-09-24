"""Two training manifests over the SAME images for a fair old-vs-new CNN comparison.

Rows = lance_landmarking/manifest.csv rows whose new-protocol automatic label
passed QC (autolabels/qc_final.csv), in the original manifest order, so
splits.split_samples() gives identical train/val/test splits for both.

  lance_landmarking/manifest_oldproto_qc.csv  old (v2) points, click-order errors fixed
  lance_landmarking/manifest_newproto.csv     new (v1.3) points: Right 42, Left 40, Bottom 38

Paths stay relative to lance_landmarking/, so the files also work on the cluster copy.
"""
import csv, json, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from autolabel import fix_order, point_order  # noqa: E402

LANCE = "/home/labradorite/g0-splits-project/lance_landmarking/"
AL = os.path.join(HERE, "..", "autolabels")


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--label-suffix", default="", help='e.g. "_distal" to use autolabels/labels_<View>_distal.csv')
    ap.add_argument("--old-out", default="manifest_oldproto_qc.csv")
    ap.add_argument("--new-out", default="manifest_newproto.csv")
    a = ap.parse_args()
    passed = {(r["view"], r["key"]) for r in csv.DictReader(open(os.path.join(AL, "qc_final.csv")))
              if r["status"] == "pass"}
    labels = {}
    for v in ("Right", "Left", "Bottom"):
        ids = point_order(v)
        f = os.path.join(AL, f"labels_{v}{a.label_suffix}.csv")
        if not os.path.exists(f):  # variant only defined for some views: fall back to the base labels
            f = os.path.join(AL, f"labels_{v}.csv")
        for r in csv.DictReader(open(f)):
            labels[(v, r["key"])] = [[round(float(r[f"{i}_x"]), 2), round(float(r[f"{i}_y"]), 2)] for i in ids]
    rows = list(csv.DictReader(open(LANCE + "manifest.csv")))
    cols = list(rows[0].keys())
    old_out, new_out = [], []
    for r in rows:
        k = (r["angle"], r["key"])
        if k not in passed or k not in labels:
            continue
        old = fix_order(r["angle"], np.array(json.loads(r["landmarks_px_json"]), float))
        o = dict(r, landmarks_px_json=json.dumps(np.round(old, 2).tolist()))
        n = dict(r, landmarks_px_json=json.dumps(labels[k]), n_expected=len(labels[k]), n_found=len(labels[k]))
        old_out.append(o)
        new_out.append(n)
    for name, out in ((a.old_out, old_out), (a.new_out, new_out)):
        with open(LANCE + name, "w", newline="") as fh:
            w = csv.DictWriter(fh, cols)
            w.writeheader()
            w.writerows(out)
        by = {}
        for r in out:
            by[r["angle"]] = by.get(r["angle"], 0) + 1
        print(name, by, "points:", {r["angle"]: r["n_expected"] for r in out})


if __name__ == "__main__":
    main()
