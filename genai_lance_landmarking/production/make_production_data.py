"""Training data for the production (protocol v1.4) landmark models.

Writes, in this folder (genai_lance_landmarking/production/), with image paths relative to it
(../raw_images, ../landmarked_images: the genai copies of the images):
  manifest_v14.csv   v1.4 points (Right 42, Left 40, Bottom 38) for every image whose
                     automatic label passed QC (autolabels/qc_final.csv). Right/Left use the
                     v1.4 distal dorsal start (labels_<View>_distal.csv).
  folds_v14.json     {family: fold 0..K-1}. Families (cross + replicate) are spread over the
                     folds within each cross type, balancing image counts, so every fold has a
                     proportional mix of groups and siblings never sit on both sides of a
                     train/test boundary. The same assignment is used for all three views.

usage: python make_production_data.py [--folds 5] [--seed 42]
"""
import argparse, csv, json, os, random, sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
CNN = os.path.abspath(os.path.join(ROOT, "..", "lance_landmarking", "cnn"))
AL = os.path.join(ROOT, "autolabels")
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, CNN)
from autolabel import point_order  # noqa: E402
from splits import family_of  # noqa: E402

SUFFIX = {"Right": "_distal", "Left": "_distal", "Bottom": ""}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--folds", type=int, default=5)
    ap.add_argument("--seed", type=int, default=42)
    a = ap.parse_args()

    passed = {(r["view"], r["key"]) for r in csv.DictReader(open(os.path.join(AL, "qc_final.csv")))
              if r["status"] == "pass"}
    labels = {}
    for v in ("Right", "Left", "Bottom"):
        ids = point_order(v)
        for r in csv.DictReader(open(os.path.join(AL, f"labels_{v}{SUFFIX[v]}.csv"))):
            labels[(v, r["key"])] = [[round(float(r[f"{i}_x"]), 2), round(float(r[f"{i}_y"]), 2)] for i in ids]

    rows = list(csv.DictReader(open(os.path.join(CNN, "manifest.csv"))))
    # re-point the image paths from lance_landmarking/cnn/ to this folder: "../raw_images/<group>/..."
    # already resolves to genai_lance_landmarking/raw_images; the marked images are ../landmarked_images
    for r in rows:
        for c in ("marked_tiff", "txt"):
            r[c] = r[c].replace("../marked_images/", "../landmarked_images/")
    out = []
    for r in rows:
        k = (r["angle"], r["key"])
        if k in passed and k in labels:
            out.append(dict(r, landmarks_px_json=json.dumps(labels[k]), landmark_source="autolabel_v1.4",
                            n_expected=len(labels[k]), n_found=len(labels[k])))
    with open(os.path.join(HERE, "manifest_v14.csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, list(rows[0].keys()))
        w.writeheader()
        w.writerows(out)

    # folds over ALL families in the full manifest, so images that failed label QC
    # (predicted later by the ensemble) still have a defined family
    # balanced: within each group, largest families first, each to the fold that is
    # currently smallest in that group (ties broken by overall size, then at random)
    fams = defaultdict(lambda: defaultdict(int))
    for r in rows:
        fams[r["group"]][family_of(r["key"])] += 1
    rng = random.Random(a.seed)
    folds, total = {}, [0] * a.folds
    for g in sorted(fams):
        ids = sorted(fams[g])
        rng.shuffle(ids)
        ids.sort(key=lambda f: -fams[g][f])
        in_group = [0] * a.folds
        for f in ids:
            if f in folds:  # a family listed under two groups keeps its first fold
                continue
            k = min(range(a.folds), key=lambda i: (in_group[i], total[i], rng.random()))
            folds[f] = k
            in_group[k] += fams[g][f]
            total[k] += fams[g][f]
    json.dump(folds, open(os.path.join(HERE, "folds_v14.json"), "w"), indent=0, sort_keys=True)

    n = defaultdict(lambda: [0] * a.folds)
    for r in out:
        n[r["angle"]][folds[family_of(r["key"])]] += 1
    print("manifest_v14.csv:", {v: sum(c) for v, c in n.items()}, "images")
    print("folds_v14.json:", len(folds), "families; images per fold:", dict(n))


if __name__ == "__main__":
    main()
