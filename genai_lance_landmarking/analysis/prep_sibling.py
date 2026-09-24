"""Backcross sibling-family datasets for the old (v2 human) and new (v1.4) protocols.

Same individuals for both protocols: LBX and PBX specimens whose new-protocol
label passed QC and whose family (splits.family_of: ID without the -vNN
individual suffix) has at least 3 such individuals. New labels: v1.4 for Right
and Left (autolabels/labels_<View>_distal.csv, dorsal curve starting at the
window's proximal end), v1.3 = v1.4 for the Dorsal face (labels_Bottom.csv).

writes data/sib_<View>_{old,new}.csv: key, group, family, session, x1, y1, ...
"""
import csv, json, os, sys
from collections import Counter
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, "/home/labradorite/g0-splits-project/lance_landmarking/cnn")
from autolabel import fix_order, point_order  # noqa: E402
from splits import family_of  # noqa: E402

LANCE = "/home/labradorite/g0-splits-project/lance_landmarking/cnn/"  # the manifests live here; their image paths are relative to it
AL = os.path.join(ROOT, "autolabels")
man = {(r["angle"], r["key"]): r for r in csv.DictReader(open(LANCE + "manifest.csv"))}
qc = {(r["view"], r["key"]): r["status"] for r in csv.DictReader(open(os.path.join(AL, "qc_final.csv")))}

for view in ("Right", "Left", "Bottom"):
    lab_file = f"labels_{view}_distal.csv" if view != "Bottom" else "labels_Bottom.csv"
    labels = {r["key"]: r for r in csv.DictReader(open(os.path.join(AL, lab_file)))}
    ids = point_order(view)
    keys = [k for k in labels if qc.get((view, k)) == "pass" and man[(view, k)]["group"] in ("LBX", "PBX")]
    fam = Counter(family_of(k) for k in keys)
    keys = sorted(k for k in keys if fam[family_of(k)] >= 3)
    os.makedirs(os.path.join(HERE, "data"), exist_ok=True)
    with open(os.path.join(HERE, "data", f"sib_{view}_old.csv"), "w", newline="") as fo, \
            open(os.path.join(HERE, "data", f"sib_{view}_new.csv"), "w", newline="") as fn:
        wo, wn = csv.writer(fo), csv.writer(fn)
        first = True
        for k in keys:
            m = man[(view, k)]
            old = fix_order(view, np.array(json.loads(m["landmarks_px_json"]), float))
            new = [(float(labels[k][f"{i}_x"]), float(labels[k][f"{i}_y"])) for i in ids]
            meta = [k, m["group"], family_of(k), "cam2560" if m["image_width"] == "2560" else "cam3840"]
            if first:
                wo.writerow(["key", "group", "family", "session"] + [f"{a}{i + 1}" for i in range(len(old)) for a in "xy"])
                wn.writerow(["key", "group", "family", "session"] + [f"{i}_{a}" for i in ids for a in "xy"])
                first = False
            wo.writerow(meta + [f"{v:.2f}" for v in old.ravel()])
            wn.writerow(meta + [f"{v:.2f}" for p in new for v in p])
    f2 = Counter(family_of(k) for k in keys)
    print(f"{view}: {len(keys)} backcross individuals in {len(f2)} families (sizes {sorted(f2.values(), reverse=True)})")
