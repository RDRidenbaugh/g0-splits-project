"""Old vs new protocol configurations for the same specimens, ready for geomorph.

Inputs: lance_landmarking/manifest.csv (old human digitization, pixels) and
autolabels/labels_<View>.csv + autolabels/qc.csv (new protocol).
Only specimens whose new-protocol labels passed QC are used, for BOTH protocols,
so the two are compared on identical specimens.

Writes analysis/data/<View>_old.csv, <View>_new.csv (key, group, class, species,
session, then x1,y1,...) and <View>_sliders_new.csv (before, slide, after; 1-indexed).

class: lecontei / pinetum (Parents + Non_Laying_Parents, by ID prefix ll/lx vs np/px),
       F1, LBX, PBX.  session: cam2560 (1260 px/mm) or cam3840 (927 px/mm).
"""
import csv, json, os, re, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
sys.path.insert(0, os.path.join(ROOT, "tools"))
from autolabel import fix_order  # noqa: E402

LANCE = "/home/labradorite/g0-splits-project/lance_landmarking/"
SCHEMA = json.load(open(os.path.join(ROOT, "landmark_schema.json")))
OUT = os.path.join(HERE, "data")


def klass(group, key):
    if group in ("Parents", "Non_Laying_Parents"):
        return "lecontei" if re.match(r"l[lx]", key) else "pinetum"
    return group


def sliders(view):
    pts = [p["id"] for p in SCHEMA["views"][view]["points"]]
    ix = {p: i + 1 for i, p in enumerate(pts)}
    rows = []
    for c in SCHEMA["views"][view]["curves"]:
        semis = [f"{c['id']}{k + 1}" for k in range(c["n_semilandmarks"])]
        if c["id"].endswith(".window"):
            s = view[0]
            tops = [f"{s}{i:02d}" for i in range(12, 17)]
            for k, sm in enumerate(semis):
                rows.append((ix[tops[k]], ix[sm], ix[tops[k + 1]]))
            continue
        chain = [c["start"]] + semis + [c["end"]]
        for k in range(1, len(chain) - 1):
            rows.append((ix[chain[k - 1]], ix[chain[k]], ix[chain[k + 1]]))
    return rows


def main():
    os.makedirs(OUT, exist_ok=True)
    qc = {(r["view"], r["key"]): r for r in csv.DictReader(open(os.path.join(ROOT, "autolabels", "qc_final.csv")))}
    man = {(r["angle"], r["key"]): r for r in csv.DictReader(open(LANCE + "manifest.csv"))}
    for view in ("Right", "Left", "Bottom"):
        new = {r["key"]: r for r in csv.DictReader(open(os.path.join(ROOT, "autolabels", f"labels_{view}.csv")))}
        keys = sorted(k for k in new if qc.get((view, k), {}).get("status") == "pass")
        ncol = [c for c in next(iter(new.values())) if c.endswith("_x") or c.endswith("_y")]
        with open(os.path.join(OUT, f"{view}_new.csv"), "w", newline="") as fn, \
                open(os.path.join(OUT, f"{view}_old.csv"), "w", newline="") as fo:
            wn, wo = csv.writer(fn), csv.writer(fo)
            meta = ["key", "group", "class", "species", "session"]
            n_old = None
            for k in keys:
                m = man[(view, k)]
                old = fix_order(view, np.array(json.loads(m["landmarks_px_json"]), float))
                if n_old is None:
                    n_old = len(old)
                    wo.writerow(meta + [f"{a}{i + 1}" for i in range(n_old) for a in "xy"])
                    wn.writerow(meta + ncol)
                cl = klass(m["group"], k)
                sp = cl if cl in ("lecontei", "pinetum") else ""
                ses = "cam2560" if m["image_width"] == "2560" else "cam3840"
                row = [k, m["group"], cl, sp, ses]
                wo.writerow(row + [f"{v:.2f}" for v in old.ravel()])
                wn.writerow(row + [new[k][c] for c in ncol])
        with open(os.path.join(OUT, f"{view}_sliders_new.csv"), "w", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["before", "slide", "after"])
            w.writerows(sliders(view))
        print(view, len(keys), "specimens")


if __name__ == "__main__":
    main()
