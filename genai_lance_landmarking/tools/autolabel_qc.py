"""Pass/fail gate for the automatic labels: autolabels/qc.csv + labels -> autolabels/qc_final.csv.

The old human points are an independent check of the automatic outline:
  * snapped anchors: each must lie within TOL px of the old human point it came
    from. Right/Left: apex (Right), heel-ventral junction, heel notch, suture
    ventral ends. The heel notch gets HEEL_TOL instead: on the Left face the old
    point 1 was usually clicked on an internal line 40-60 px inside the heel,
    while the new point sits on the outline where the heel edge meets the
    structure above it; only a much larger gap (a flap or the basal process
    merged into the outline, typically 100-250 px) is an error.
  * dorsal curve (fully automatic): the old human dorsal-edge points (Right
    31-36, Left 27-32) must lie within TOL px of it.
  * Dorsal face: both apices within TOL px. Suture ends only get a gross check
    (SUTURE_TOL): in the Parents images the old "topmost point of the suture"
    was often clicked on the suture line inside the tip, not at the edge, so
    their offset measures the old definition, not the outline.
  * heel curve (Right/Left): old point 2 (the old "furthest protruding point of
    the heel", on the heel's proximal edge) must lie within HEEL_CURVE_TOL px of
    it; a heel curve that wandered onto a flap or membrane fails.
  * Dorsal shoulders: each shoulder's distance from the long axis divided by the
    same for its 4th-from-apex suture must be within LEN_MAD robust SDs of the
    camera median; a shoulder that climbed onto a flap sits far out.
  * lateral height at suture 1 (R04/L04 to the dorsal-curve start R18/L18, over
    the lance length R02->R01) within HEIGHT_MAD robust SDs of its view x camera
    median: a dorsal curve that starts on the golden basal flap (flap touching the
    dorsal edge) makes the lance look far too tall there.
  * every traced curve's length within LEN_MAD robust SDs of its view x camera median.
  * images whose shoulder rule declined (Dorsal) already failed at build time.
TOL and SUTURE_TOL are in pixels at 927 px/mm and scale x1.36 for the 1260 px/mm camera.

usage: python autolabel_qc.py [--tol 25] [--heel-tol 100] [--suture-tol 80] [--len-mad 5]
"""
import argparse, csv, json, os, sys
from collections import Counter, defaultdict
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from autolabel import fix_order  # noqa: E402

AL = os.path.join(HERE, "..", "autolabels")
LANCE = "/home/labradorite/g0-splits-project/lance_landmarking/"
SCHEMA = json.load(open(os.path.join(HERE, "..", "landmark_schema.json")))
# old 30 (Right) / 26 (Left) sit proximal to where the new dorsal curve starts (R18/L18), so they are not used
DORSAL_OLD = {"Right": range(31, 37), "Left": range(27, 33)}


def dist_to_polyline(p, poly):
    a, b = poly[:-1], poly[1:]
    ab = b - a
    t = np.clip(((p - a) * ab).sum(1) / np.maximum((ab * ab).sum(1), 1e-9), 0, 1)
    return np.min(np.linalg.norm(a + t[:, None] * ab - p, axis=1))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tol", type=float, default=25.0)
    ap.add_argument("--heel-tol", type=float, default=100.0)
    ap.add_argument("--heel-curve-tol", type=float, default=50.0)
    ap.add_argument("--suture-tol", type=float, default=80.0)
    ap.add_argument("--len-mad", type=float, default=5.0)
    ap.add_argument("--height-mad", type=float, default=3.0)
    a = ap.parse_args()
    man = {(r["angle"], r["key"]): r for r in csv.DictReader(open(LANCE + "manifest.csv"))}
    rows = list(csv.DictReader(open(os.path.join(AL, "qc.csv"))))
    labels = {}
    for v in ("Right", "Left", "Bottom"):
        for r in csv.DictReader(open(os.path.join(AL, f"labels_{v}.csv"))):
            labels[(v, r["key"])] = r
    for r in rows:
        r["session"] = "cam2560" if man[(r["view"], r["key"])]["image_width"] == "2560" else "cam3840"
    lens = defaultdict(list)
    for r in rows:
        if r["status"] == "ok":
            for c, v in r.items():
                if c.startswith("len_") and v:
                    lens[(r["view"], r["session"], c)].append(np.log(max(float(v), 1e-3)))
    lim = {}
    for k, v in lens.items():
        v = np.array(v)
        med = np.median(v)
        mad = 1.4826 * np.median(np.abs(v - med)) or 1e-9
        lim[k] = (med - a.len_mad * mad, med + a.len_mad * mad)

    def P_of(view, key):
        lab = labels[(view, key)]
        return lambda pid: np.array([float(lab[pid + "_x"]), float(lab[pid + "_y"])])

    def shoulder_ratios(view, key):
        P = P_of(view, key)
        tip = (P("B01") + P("B02")) / 2
        ax = (tip - P("B11")) / np.linalg.norm(tip - P("B11"))
        nr = np.array([-ax[1], ax[0]])
        lat = lambda q: abs((P(q) - P("B11")) @ nr)
        return lat("B12") / lat("B06"), lat("B13") / lat("B10")

    def height_ratio(view, key):
        P = P_of(view, key)
        s_ = view[0]
        return np.linalg.norm(P(f"{s_}18") - P(f"{s_}04")) / np.linalg.norm(P(f"{s_}01") - P(f"{s_}02"))

    hts = defaultdict(list)
    for r in rows:
        if r["view"] in ("Right", "Left") and r["status"] == "ok":
            hts[(r["view"], r["session"])].append(np.log(height_ratio(r["view"], r["key"])))
    ht_lim = {}
    for k, v in hts.items():
        v = np.array(v)
        med = np.median(v)
        mad = 1.4826 * np.median(np.abs(v - med))
        ht_lim[k] = (med - a.height_mad * mad, med + a.height_mad * mad)

    sh = defaultdict(list)
    for r in rows:
        if r["view"] == "Bottom" and r["status"] == "ok":
            sh[r["session"]] += [np.log(x) for x in shoulder_ratios("Bottom", r["key"])]
    sh_lim = {}
    for k, v in sh.items():
        v = np.array(v)
        med = np.median(v)
        mad = 1.4826 * np.median(np.abs(v - med))
        sh_lim[k] = (med - a.len_mad * mad, med + a.len_mad * mad)

    for r in rows:
        view, key = r["view"], r["key"]
        if r["status"] != "ok":
            r["final"], r["why"] = "fail", r.get("reason", "")
            continue
        s = 1260 / 927 if r["session"] == "cam2560" else 1.0
        lab = labels[(view, key)]
        P = lambda pid: np.array([float(lab[pid + "_x"]), float(lab[pid + "_y"])])
        old = fix_order(view, np.array(json.loads(man[(view, key)]["landmarks_px_json"]), float))
        why = []
        for p in SCHEMA["views"][view]["points"]:
            if p["role"] != "anchor" or not p.get("on_outline") or not p.get("old_protocol_point"):
                continue
            d = np.linalg.norm(P(p["id"]) - old[p["old_protocol_point"] - 1])
            is_suture = view == "Bottom" and p["id"] not in ("B01", "B02")
            tol = a.suture_tol if is_suture else a.heel_tol if p["id"] in ("R03", "L03") else a.tol
            if d > tol * s:
                why.append(f"{p['id']} {d:.0f}px")
        if view in DORSAL_OLD:
            v0 = view[0]
            poly = np.array([P(f"{v0}18")] + [P(f"{v0}.dorsal{k}") for k in range(1, 11)] + [P(f"{v0}01")])
            dd = [dist_to_polyline(old[i - 1], poly) for i in DORSAL_OLD[view]]
            if max(dd) > a.tol * s:
                why.append(f"dorsal edge {max(dd):.0f}px")
            poly = np.array([P(f"{v0}03")] + [P(f"{v0}.heel{k}") for k in range(1, 5)] + [P(f"{v0}02")])
            dh = dist_to_polyline(old[1], poly)
            if dh > a.heel_curve_tol * s:
                why.append(f"heel curve {dh:.0f}px")
            lo, hi = ht_lim[(view, r["session"])]
            if not lo <= np.log(height_ratio(view, key)) <= hi:
                why.append(f"height at suture 1 {height_ratio(view, key):.2f}")
        if view == "Bottom":
            lo, hi = sh_lim[r["session"]]
            for name, x in zip(("B12", "B13"), shoulder_ratios(view, key)):
                if not lo <= np.log(x) <= hi:
                    why.append(f"{name} lateral")
        for c, v in r.items():
            if c.startswith("len_") and v:
                lo, hi = lim[(view, r["session"], c)]
                if not lo <= np.log(max(float(v), 1e-3)) <= hi:
                    why.append(f"{c[4:]} length")
        r["final"] = "fail" if why else "pass"
        r["why"] = "; ".join(why)
    for r in rows:
        r["status"], r["reason"] = r.pop("final"), r.pop("why")
    with open(os.path.join(AL, "qc_final.csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"tolerance {a.tol} px (heel notch {a.heel_tol}, Dorsal sutures {a.suture_tol}), x1.36 for the 1260 px/mm camera")
    for view in ("Right", "Left", "Bottom"):
        vr = [r for r in rows if r["view"] == view]
        by = Counter((r["group"], r["status"]) for r in vr)
        print(f"\n{view}: pass {sum(r['status'] == 'pass' for r in vr)}/{len(vr)}")
        for g in sorted({r["group"] for r in vr}):
            p, f = by[(g, "pass")], by[(g, "fail")]
            print(f"  {g:20s} {p:3d}/{p + f:3d} ({100 * p / (p + f):.0f}%)")
        reasons = Counter()
        for r in vr:
            if r["status"] == "fail":
                for part in r["reason"].split("; "):
                    reasons[part.split(" ")[0] + (" " + part.split(" ")[1] if part.startswith("dorsal") or part.startswith("shoulder") else "")] += 1
        print("  fail reasons:", dict(reasons.most_common(8)))


if __name__ == "__main__":
    main()
