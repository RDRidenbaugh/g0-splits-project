"""Turn landmark predictions into geomorph-ready coordinate tables in mm (step 2 of 2).

Reads predictions_px_<View>.csv from landmark_images.py and writes, per view, to --out-dir:

  Lance<View>_v14_XY.csv       one row per individual: ID, species, group, session, px_per_mm,
                               source, key, qc_flags, qc_pass, then X1, Y1, ..., Xn, Yn in mm
                               (image axes: x right, y down). Same layout as the PRIME
                               saw tables, so arrayspecs(df[, first_X:last_Y], n, 2) works.
  Lance<View>_v14_sliders.csv  before / slide / after (1-indexed) for gpagen(curves = ...)
  landmark_key_v14.csv         view, number (1..n), protocol ID (R01, R.dorsal3, ...), role, definition
  export_report.txt            counts, dropped duplicates, missing species

Species: sample_sheet.csv (ID, species) first; otherwise the cross type (LBX, PBX, F1), or for
parents the ID prefix (LL/LX = Lecontei, NP/PX = Pinetum). Add new individuals to sample_sheet.csv
when the rule cannot tell.

QC: qc_pass is TRUE when landmark_images.py raised no flag. After looking at the overlays, record
decisions in qc_review.csv (view, key, decision = keep | drop, note); they override the flags.
When an individual has several images of one view, the one kept is: passing QC, then smallest
model disagreement; the others are listed in the report.

usage: python export_geomorph.py [--pred-dir output] [--out-dir output/geomorph]
"""
import argparse, csv, json, os, re
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCHEMA = json.load(open(HERE.parent / "landmark_schema.json"))
SPECIES_LEVELS = ["Lecontei", "LBX", "F1", "PBX", "Pinetum"]


def sliders(view):
    """(before, slide, after) rows, 1-indexed; the window scallops slide between suture ends."""
    pts = [p["id"] for p in SCHEMA["views"][view]["points"]]
    ix = {p: i + 1 for i, p in enumerate(pts)}
    rows = []
    for c in SCHEMA["views"][view]["curves"]:
        semis = [f"{c['id']}{k + 1}" for k in range(c["n_semilandmarks"])]
        if c["id"].endswith(".window"):
            tops = [f"{view[0]}{i:02d}" for i in range(12, 17)]
            rows += [(ix[tops[k]], ix[sm], ix[tops[k + 1]]) for k, sm in enumerate(semis)]
            continue
        chain = [c["start"]] + semis + [c["end"]]
        rows += [(ix[chain[k - 1]], ix[chain[k]], ix[chain[k + 1]]) for k in range(1, len(chain) - 1)]
    return rows


def species_of(ID, group, sheet):
    if ID in sheet:
        return sheet[ID]
    if group in ("LBX", "PBX", "F1"):
        return group
    if group in ("Parents", "Non_Laying_Parents"):
        return "Lecontei" if re.match(r"l[lx]", ID, re.I) else "Pinetum" if re.match(r"(np|px)", ID, re.I) else ""
    return ""


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--pred-dir", default=str(HERE / "output"))
    ap.add_argument("--out-dir", default=None, help="default: <pred-dir>/geomorph")
    ap.add_argument("--sample-sheet", default=str(HERE / "sample_sheet.csv"))
    ap.add_argument("--qc-review", default=str(HERE / "qc_review.csv"))
    a = ap.parse_args()
    pred = Path(a.pred_dir)
    out = Path(a.out_dir or pred / "geomorph")
    out.mkdir(parents=True, exist_ok=True)

    sheet = {r["ID"]: r["species"] for r in csv.DictReader(open(a.sample_sheet))} if os.path.exists(a.sample_sheet) else {}
    review = {}
    if os.path.exists(a.qc_review):
        review = {(r["view"], r["key"]): r["decision"].strip().lower() for r in csv.DictReader(open(a.qc_review))}

    with open(out / "landmark_key_v14.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["view", "number", "id", "role", "definition"])
        for view, d in SCHEMA["views"].items():
            for i, p in enumerate(d["points"], 1):
                w.writerow([view, i, p["id"], p["role"], p.get("definition", f"semilandmark on {p.get('curve')}")])

    report = []
    for view in ("Right", "Left", "Bottom"):
        f = pred / f"predictions_px_{view}.csv"
        if not f.exists():
            continue
        rows = list(csv.DictReader(open(f)))
        n = len(SCHEMA["views"][view]["points"])
        by_id = defaultdict(list)
        for r in rows:
            decision = review.get((view, r["key"]))
            r["qc_pass"] = decision == "keep" if decision in ("keep", "drop") else not r["flags"]
            by_id[r["ID"]].append(r)
        kept, dups, nosp, noscale = [], [], [], []
        for ID, rs in by_id.items():
            rs.sort(key=lambda r: (not r["qc_pass"], float(r["spread_px"])))
            kept.append(rs[0])
            dups += [f"{view}\t{ID}\tkept {rs[0]['key']}\tdropped {r['key']}" for r in rs[1:]]
        with open(out / f"Lance{view}_v14_XY.csv", "w", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["ID", "species", "group", "session", "px_per_mm", "source", "key", "qc_flags", "qc_pass"]
                       + [f"{c}{i}" for i in range(1, n + 1) for c in "XY"])
            for r in sorted(kept, key=lambda r: r["ID"]):
                sp = species_of(r["ID"], r["group"], sheet)
                if not sp:
                    nosp.append(r["ID"])
                if not r["px_per_mm"]:
                    noscale.append(r["ID"])
                    xy = ["NA"] * (2 * n)
                else:
                    s = float(r["px_per_mm"])
                    xy = [round(float(r[f"{c}{i}"]) / s, 5) for i in range(1, n + 1) for c in "xy"]
                w.writerow([r["ID"], sp, r["group"], r["session"], r["px_per_mm"], r["source"], r["key"],
                            r["flags"], "TRUE" if r["qc_pass"] else "FALSE"] + xy)
        with open(out / f"Lance{view}_v14_sliders.csv", "w", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["before", "slide", "after"])
            w.writerows(sliders(view))
        npass = sum(r["qc_pass"] for r in kept)
        report.append(f"{view}: {len(rows)} images -> {len(kept)} individuals ({npass} pass QC, "
                      f"{len(kept) - npass} flagged), {len(dups)} duplicate images dropped")
        if nosp:
            report.append(f"  no species (add to sample_sheet.csv): {', '.join(sorted(nosp))}")
        if noscale:
            report.append(f"  no calibration, coordinates NA: {', '.join(sorted(noscale))}")
        report += ["  " + d for d in dups]
    (out / "export_report.txt").write_text("\n".join(report) + "\n")
    print("\n".join(l for l in report if not l.startswith("  ")))
    print(f"-> {out}")


if __name__ == "__main__":
    main()
