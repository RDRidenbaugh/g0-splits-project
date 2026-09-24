"""Generalization check: old- vs new-protocol models on images neither model saw.

hard = digitized images excluded from training by the automatic QC (mostly
       flaps/membrane at the heel, dorsal margin or basal lobes) - never seen;
easy = the test split of the training manifests.
Both models are scored against the ORIGINAL human (v2) points, which exist for
every image, on measures that mean the same thing for both protocols:
  * shared anchors: points defined the same way in both protocols (apex, suture
    ends, window points; Dorsal: apices and suture ends), error in µm;
  * heel points (lateral): old points 1 and 3 vs new heel notch / heel-ventral
    junction, reported separately because their definitions differ;
  * dorsal edge (lateral): distance from the human dorsal-edge points (Right
    31-36, Left 27-32) to each model's predicted dorsal edge, in µm.
Per image the mean over points is taken; images are compared in pairs (same
image, old vs new model) with a bootstrap over images.

usage: python hard_case_eval.py   (after cnn/predict_hard_easy.sh)
"""
import csv, json, os
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
D = os.path.join(HERE, "data", "hard")
LANCE = "/home/labradorite/g0-splits-project/lance_landmarking/cnn/"  # the manifests live here; their image paths are relative to it
SCHEMA = json.load(open(os.path.join(ROOT, "landmark_schema.json")))
rng = np.random.default_rng(1)

man = {(r["angle"], r["key"]): r for r in csv.DictReader(open(LANCE + "manifest.csv"))}
HEEL_OLD = {1, 3}
DORSAL_HUMAN = {"Right": range(31, 37), "Left": range(27, 33)}
DORSAL_OLD_MODEL = {"Right": [30, 31, 32, 33, 34, 35, 36, 28, 13], "Left": [26, 27, 28, 29, 30, 31, 32, 13]}


def fix_order(view, old):
    import sys
    sys.path.insert(0, os.path.join(ROOT, "tools"))
    from autolabel import fix_order as f
    return f(view, old)


def load_pred(view, proto, s):
    out = {}
    for r in csv.DictReader(open(os.path.join(D, f"{view}_{proto}_{s}_pred.csv"))):
        v = np.array([float(r[c]) for c in list(r)[2:]]).reshape(-1, 2)
        out[r["key"]] = v
    return out


def seg_dist(p, poly):
    a, b = poly[:-1], poly[1:]
    ab = b - a
    t = np.clip(((p - a) * ab).sum(1) / np.maximum((ab * ab).sum(1), 1e-9), 0, 1)
    return np.min(np.linalg.norm(a + t[:, None] * ab - p, axis=1))


def boot_diff(a, b, B=2000):
    a, b = np.asarray(a), np.asarray(b)
    idx = rng.integers(0, len(a), (B, len(a)))
    d = np.median(b[idx], 1) - np.median(a[idx], 1)
    return np.median(b) - np.median(a), np.percentile(d, 2.5), np.percentile(d, 97.5)


def main():
    global rows
    rows = []
    for view in ("Right", "Left", "Bottom"):
        pts = SCHEMA["views"][view]["points"]
        ids = [p["id"] for p in pts]
        pairs = [(p["old_protocol_point"], ids.index(p["id"])) for p in pts
                 if p["role"] == "anchor" and p.get("old_protocol_point")]
        for s in ("easy", "hard"):
            po, pn = load_pred(view, "old", s), load_pred(view, "new", s)
            keys = sorted(set(po) & set(pn))
            m = {k: [] for k in ("anc_old", "anc_new", "heel_old", "heel_new", "dor_old", "dor_new")}
            groups = []
            for k in keys:
                r = man[(view, k)]
                human = fix_order(view, np.array(json.loads(r["landmarks_px_json"]), float))
                um = 1000 / (1260 if r["image_width"] == "2560" else 927)  # µm per px
                O, N = po[k], pn[k]
                shared = [(o, n) for o, n in pairs if o not in HEEL_OLD or view == "Bottom"]
                m["anc_old"].append(np.mean([np.linalg.norm(O[o - 1] - human[o - 1]) for o, _ in shared]) * um)
                m["anc_new"].append(np.mean([np.linalg.norm(N[n] - human[o - 1]) for o, n in shared]) * um)
                if view != "Bottom":
                    heel = [(o, n) for o, n in pairs if o in HEEL_OLD]
                    m["heel_old"].append(np.mean([np.linalg.norm(O[o - 1] - human[o - 1]) for o, _ in heel]) * um)
                    m["heel_new"].append(np.mean([np.linalg.norm(N[n] - human[o - 1]) for o, n in heel]) * um)
                    s_ = view[0]
                    polyN = N[[ids.index(f"{s_}18")] + [ids.index(f"{s_}.dorsal{i}") for i in range(1, 11)] +
                              [ids.index(f"{s_}01")]]
                    polyO = O[[i - 1 for i in DORSAL_OLD_MODEL[view]]]
                    m["dor_old"].append(np.mean([seg_dist(human[i - 1], polyO) for i in DORSAL_HUMAN[view]]) * um)
                    m["dor_new"].append(np.mean([seg_dist(human[i - 1], polyN) for i in DORSAL_HUMAN[view]]) * um)
                groups.append(r["group"])
            for meas, lab in (("anc", "shared anchors"), ("heel", "heel points (definitions differ)"),
                              ("dor", "dorsal edge")):
                if not m[f"{meas}_old"]:
                    continue
                a, b = np.array(m[f"{meas}_old"]), np.array(m[f"{meas}_new"])
                d, lo, hi = boot_diff(a, b)
                rows.append(dict(view=view, set=s, measure=lab, n=len(a),
                                 old_median_um=round(np.median(a), 1), new_median_um=round(np.median(b), 1),
                                 new_minus_old_median=f"{d:.1f} [{lo:.1f}, {hi:.1f}]",
                                 old_p90_um=round(np.percentile(a, 90), 1), new_p90_um=round(np.percentile(b, 90), 1),
                                 old_gross_pct=round(100 * np.mean(a > 50), 1), new_gross_pct=round(100 * np.mean(b > 50), 1)))
    out = os.path.join(HERE, "output", "hard_case_eval.csv")
    with open(out, "w", newline="") as fh:
        w = csv.DictWriter(fh, list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    for r in rows:
        print(f"{r['view']:6s} {r['set']:4s} {r['measure']:32s} n={r['n']:3d}  median µm old {r['old_median_um']:6.1f} new "
              f"{r['new_median_um']:6.1f}  diff {r['new_minus_old_median']:22s} p90 old {r['old_p90_um']:6.1f} new "
              f"{r['new_p90_um']:6.1f}  >50µm old {r['old_gross_pct']:5.1f}% new {r['new_gross_pct']:5.1f}%")


if __name__ == "__main__":
    main()
