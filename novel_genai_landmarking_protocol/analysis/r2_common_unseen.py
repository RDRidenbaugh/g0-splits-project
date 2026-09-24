"""Round 1 vs round 2 on the SAME never-seen images (unseen by every model in both rounds).

Round 2's never-seen set is easier than round 1's (the label fix moved flap-heavy
images into training), so rounds are compared only on images outside both
training sets. Measure: dorsal edge (distance from the human dorsal-edge points to
each model's predicted dorsal edge), in µm.  -> output/r2_common_unseen_dorsal.csv
"""
import csv, json, os
import numpy as np
from hard_case_eval import seg_dist, man, fix_order, SCHEMA, DORSAL_HUMAN, DORSAL_OLD_MODEL

HERE = os.path.dirname(os.path.abspath(__file__))


def load(path):
    return {r["key"]: np.array([float(r[c]) for c in list(r)[2:]]).reshape(-1, 2) for r in csv.DictReader(open(path))}


rows = []
for v in ("Right", "Left"):
    ids = [p["id"] for p in SCHEMA["views"][v]["points"]]
    s = v[0]
    P = {"round 1, old": f"data/hard/{v}_old_hard_pred.csv", "round 1, new": f"data/hard/{v}_new_hard_pred.csv",
         "round 2, old": f"data/hard_r2/{v}_old_hard_pred.csv", "round 2, new (fixed labels)": f"data/hard_r2/{v}_new_hard_pred.csv",
         "round 2, new distal start": f"data/hard_r2/{v}_newdistal_hard_pred.csv"}
    P = {k: load(os.path.join(HERE, f)) for k, f in P.items()}
    common = sorted(set.intersection(*[set(x) for x in P.values()]))
    for name, pr in P.items():
        d = []
        for k in common:
            r = man[(v, k)]
            hm = fix_order(v, np.array(json.loads(r["landmarks_px_json"])))
            um = 1000 / (1260 if r["image_width"] == "2560" else 927)
            X = pr[k]
            poly = X[[i - 1 for i in DORSAL_OLD_MODEL[v]]] if name.endswith("old") else \
                X[[ids.index(f"{s}18")] + [ids.index(f"{s}.dorsal{i}") for i in range(1, 11)] + [ids.index(f"{s}01")]]
            d.append(np.mean([seg_dist(hm[i - 1], poly) for i in DORSAL_HUMAN[v]]) * um)
        d = np.array(d)
        rows.append(dict(view=v, model=name, n=len(common), median_um=round(np.median(d), 1),
                         p90_um=round(np.percentile(d, 90), 1), gross_n=int(np.sum(d > 50)),
                         gross_pct=round(100 * np.mean(d > 50), 1)))
with open(os.path.join(HERE, "output", "r2_common_unseen_dorsal.csv"), "w", newline="") as fh:
    w = csv.DictWriter(fh, list(rows[0]))
    w.writeheader()
    w.writerows(rows)
for r in rows:
    print(r)
