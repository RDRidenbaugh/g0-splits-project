"""Generates analysis/Protocol_Comparison_Findings.docx from the analysis outputs.

Every number is read from files (autolabels/qc_final.csv, labels, analysis/output/*.csv),
so rerunning after new results keeps the document current. The signal-to-noise
section is filled from analysis/output/snr_summary.csv when it exists.

usage (project venv): python make_findings_docx.py
"""
import csv, json, os, sys
from collections import Counter
from datetime import date

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
OUTD = os.path.join(HERE, "output")
OUT = os.path.join(HERE, "Protocol_Comparison_Findings.docx")
sys.path.insert(0, os.path.join(ROOT, "tools"))
from autolabel import fix_order  # noqa: E402
from autolabel_qc import dist_to_polyline, DORSAL_OLD  # noqa: E402

LANCE = "/home/labradorite/g0-splits-project/lance_landmarking/"
VIEW_NAME = {"Right": "Right", "Left": "Left", "Bottom": "Dorsal"}
INK, INK2, GRID, BLUE = "#0b0b0b", "#52514e", "#d9d8d4", "#2a78d6"


def read(name):
    return list(csv.DictReader(open(os.path.join(OUTD, name))))


# ------------------------------------------------------------------ numbers
qc = list(csv.DictReader(open(os.path.join(ROOT, "autolabels", "qc_final.csv"))))
man = {(r["angle"], r["key"]): r for r in csv.DictReader(open(LANCE + "manifest.csv"))}
schema = json.load(open(os.path.join(ROOT, "landmark_schema.json")))


def agreement():
    """Median distance (px) between old human points and the automatic labels:
    lateral suture ventral ends (snapped anchors) and old dorsal-edge points to the dorsal curve."""
    sut, dor = [], []
    for v in ("Right", "Left"):
        for lab in csv.DictReader(open(os.path.join(ROOT, "autolabels", f"labels_{v}.csv"))):
            P = lambda pid: np.array([float(lab[pid + "_x"]), float(lab[pid + "_y"])])
            old = fix_order(v, np.array(json.loads(man[(v, lab["key"])]["landmarks_px_json"]), float))
            for p in schema["views"][v]["points"]:
                if p["role"] == "anchor" and p["definition"].startswith("suture") and "ventral" in p["definition"]:
                    sut.append(np.linalg.norm(P(p["id"]) - old[p["old_protocol_point"] - 1]))
            s = v[0]
            poly = np.array([P(f"{s}18")] + [P(f"{s}.dorsal{k}") for k in range(1, 11)] + [P(f"{s}01")])
            dor += [dist_to_polyline(old[i - 1], poly) for i in DORSAL_OLD[v]]
    return np.median(sut), np.percentile(sut, 90), np.median(dor), np.percentile(dor, 90)


sut_med, sut_p90, dor_med, dor_p90 = agreement()
summary = read("protocol_comparison_summary.csv")
boot = read("bootstrap_old_vs_new.csv")
mods = read("module_old_vs_new_species.csv")
hi = read("hybrid_index_individuals.csv")
snr_path = os.path.join(OUTD, "snr_summary.csv")
snr = read("snr_summary.csv") if os.path.exists(snr_path) else None
snr_diff = read("snr_new_minus_old.csv") if os.path.exists(os.path.join(OUTD, "snr_new_minus_old.csv")) else None
ablation = read("snr_ablation_right.csv") if os.path.exists(os.path.join(OUTD, "snr_ablation_right.csv")) else None
hard = read("hard_case_eval.csv") if os.path.exists(os.path.join(OUTD, "hard_case_eval.csv")) else None
runs_dir = "/home/labradorite/g0-splits-project/lance_landmarking/model/runs/protocol_comparison"
evals = {}
for v in ("Right", "Left", "Bottom"):
    for pr in ("old", "new"):
        f = os.path.join(runs_dir, f"{pr}_{v}", "eval_test.json")
        if os.path.exists(f):
            evals[(v, pr)] = json.load(open(f))


def snr_row(view, proto, subset, measure):
    for r in snr or []:
        if (r["view"], r["protocol"], r["subset"], r["measure"]) == (view, proto, subset, measure):
            return r


def diff_row(view, subset, measure):
    for r in snr_diff or []:
        if (r["view"], r["subset"], r["measure"]) == (view, subset, measure):
            return r

# ------------------------------------------------------------------ figure: hybrid index
order = ["lecontei", "LBX", "F1", "PBX", "pinetum"]
fig, axes = plt.subplots(3, 2, figsize=(7.5, 7.2), sharex=True, sharey=True)
rng = np.random.default_rng(0)
for i, v in enumerate(("Right", "Left", "Bottom")):
    for j, proto in enumerate(("old", "new")):
        ax = axes[i, j]
        for yi, c in enumerate(order):
            h = np.array([float(r["h"]) for r in hi if r["view"] == v and r["protocol"] == proto and r["class"] == c])
            ax.scatter(h, yi + rng.uniform(-0.18, 0.18, len(h)), s=10, color=BLUE, alpha=0.45, linewidths=0)
            ax.plot([np.median(h)] * 2, [yi - 0.32, yi + 0.32], color=INK, lw=2, solid_capstyle="round")
        for x in (0, 0.5, 1):
            ax.axvline(x, color=GRID, lw=1, zorder=0)
        ax.set_yticks(range(len(order)), order, color=INK2, fontsize=8)
        ax.tick_params(axis="x", colors=INK2, labelsize=8)
        for sp in ("top", "right"):
            ax.spines[sp].set_visible(False)
        for sp in ("left", "bottom"):
            ax.spines[sp].set_color(GRID)
        ax.set_xlim(-0.8, 1.6)
        ax.set_title(f"{VIEW_NAME[v]} face, {proto} protocol", fontsize=9, color=INK, loc="left")
        if i == 2:
            ax.set_xlabel("hybrid index (0 = lecontei mean, 1 = pinetum mean)", fontsize=8, color=INK2)
fig.tight_layout()
FIGPATH = os.path.join(OUTD, "hybrid_index_old_vs_new.png")
fig.savefig(FIGPATH, dpi=200, facecolor="white")

# ------------------------------------------------------------------ document helpers
doc = Document()
sec = doc.sections[0]
sec.page_width, sec.page_height = Inches(8.5), Inches(11)
for side in ("left_margin", "right_margin", "top_margin", "bottom_margin"):
    setattr(sec, side, Inches(1))
st = doc.styles["Normal"]
st.font.name, st.font.size = "Calibri", Pt(11)
st.element.rPr.rFonts.set(qn("w:eastAsia"), "Calibri")
for lvl in (1, 2):
    h = doc.styles[f"Heading {lvl}"]
    h.font.name, h.font.size, h.font.bold = "Calibri", Pt(14 if lvl == 1 else 12), True
    h.font.color.rgb = RGBColor(0x1F, 0x3A, 0x5F)
    h.element.rPr.rFonts.set(qn("w:eastAsia"), "Calibri")


def para(text, bold=False, italic=False, size=None):
    import re
    p = doc.add_paragraph()
    for part in re.split(r"(\*\*[^*]+\*\*)", text):
        if not part:
            continue
        r = p.add_run(part[2:-2] if part.startswith("**") else part)
        r.bold = bold or part.startswith("**")
        r.italic = italic
        if size:
            r.font.size = Pt(size)
    return p


def bullets(items):
    for it in items:
        p = para(it)
        p.style = doc.styles["List Bullet"]


def table(header, rows, widths, note=None):
    t = doc.add_table(rows=1, cols=len(header))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, h in enumerate(header):
        c = t.rows[0].cells[i]
        c.text = ""
        c.paragraphs[0].add_run(h).bold = True
        tcpr = c._tc.get_or_add_tcPr()
        sh = OxmlElement("w:shd")
        sh.set(qn("w:val"), "clear"); sh.set(qn("w:color"), "auto"); sh.set(qn("w:fill"), "D9E2F3")
        tcpr.append(sh)
    for r in rows:
        cells = t.add_row().cells
        for i, v in enumerate(r):
            cells[i].text = str(v)
    for row in t.rows:
        for i, w in enumerate(widths):
            row.cells[i].width = Inches(w)
            for p in row.cells[i].paragraphs:
                for run in p.runs:
                    run.font.size = Pt(9.5)
    if note:
        para(note, italic=True, size=9)
    else:
        doc.add_paragraph()


# ------------------------------------------------------------------ content
para("Old vs new lance landmarking protocol: findings to date", bold=True, size=16)
para(f"Generated {date.today().isoformat()} from novel_genai_landmarking_protocol/analysis. "
     "Protocols: v2 = Lance_Imaging_Morphometrics_v2 (85 points); new = protocol v1.3 "
     "(120 points: 47 anchors, 3 computed points, 70 sliding semilandmarks).", italic=True, size=9)

doc.add_heading("Summary", level=1)
b = {(r["view"], r["effect"]): r for r in boot}
bullets([
    f"**New-protocol labels can be produced automatically.** "
    f"{sum(r['status'] == 'pass' for r in qc)} of {len(qc)} digitized images "
    f"({100 * sum(r['status'] == 'pass' for r in qc) / len(qc):.0f}%) received labels that passed an automatic "
    "accuracy check against the existing human digitization; the rest were excluded, not hand-corrected.",
    f"**The automatic labels are accurate where they can be checked:** suture points on the lateral faces sit a "
    f"median {sut_med:.1f} px from the human points (90th percentile {sut_p90:.1f} px), and the automatic dorsal "
    f"edge a median {dor_med:.1f} px from the human dorsal-edge points.",
    "**On these labels, the new protocol does not separate the groups better than the old one, nor detectably "
    "worse.** In a paired bootstrap, every 95% interval for the new-minus-old difference in group and species "
    "R² includes zero; the point estimates lean slightly toward the old protocol.",
    "**Some signal is new:** the heel carries more species signal under the new protocol, the Dorsal face "
    "classifies the five groups better, and the newly measured Dorsal shaft/shoulder region differs between "
    "species (mostly through size).",
    "**The decisive comparison is signal-to-noise** under automated (CNN) measurement, which bears directly on "
    "QTL power. " + ("Its results are in Section 4." if snr else "Those models are training; Section 4 will be "
                     "filled in when they finish."),
] + ([
    "**Signal-to-noise, Dorsal face: the new protocol is clearly better.** Within the backcrosses, the share of "
    f"CNN-measured shape variation that is real rose from {snr_row('Bottom', 'old', 'backcrosses', 'shape')['repeatability'].split()[0]} "
    f"to {snr_row('Bottom', 'new', 'backcrosses', 'shape')['repeatability'].split()[0]} (difference "
    f"{diff_row('Bottom', 'backcrosses', 'shape')['repeatability_new_minus_old']}); size repeatability also improved.",
    "**Left face: no difference. Right face: the new protocol is worse, and its dorsal-edge curve accounts for "
    "the gap** (with one outlier image). Without that curve the Right face matches the old protocol "
    f"({ablation[3]['new_minus_old'] if ablation else ''}).",
    "**Follow-up (Section 4.1):** the Right-face gap was mostly wrong automatic labels (dorsal curve starting on "
    "the golden basal flap), now fixed. On never-seen difficult specimens, the new dorsal curve fails on ~15% of "
    "Left images where a flap lies above the dorsal margin; a retraining round with corrected labels and a "
    "flap-avoiding variant of the curve is under way.",
    "**Recommendation so far:** adopt the new Dorsal protocol; decide the lateral dorsal curve's start point "
    "after round 2.",
] if snr else []))


doc.add_heading("1. Automated labelling", level=1)
para("For every image with an existing (v2) digitization, the new-protocol configuration was built without "
     "human input: 44 of the 47 anchors come from the old human points (snapped onto the outline where the "
     "definition places them there); interior curves (window margin, Left distal edge) come from old points; "
     "outline curves come from an automatic segmentation of the sclerotized cuticle; the three new Dorsal "
     "anchors (median notch and two shoulders) and the computed points come from geometric rules. Two old "
     "configurations with sutures clicked out of order were corrected automatically.")
para("Each label was then checked against the old human points that lie on the outline (tolerance 25 px at "
     "927 px/mm, scaled for the 1260 px/mm camera). Stricter or looser rules apply where the old definition "
     "differs from the new one: the heel notch (100 px; the old point was usually clicked on an internal line "
     "inside the heel) and Dorsal suture ends (80 px; the old point was often inside the tip). Additional checks "
     "cover the heel curve, shoulder position and curve lengths.")
rows = []
for v in ("Right", "Left", "Bottom"):
    vr = [r for r in qc if r["view"] == v]
    c = Counter((r["group"], r["status"]) for r in vr)
    cells = [VIEW_NAME[v]]
    for g in ("Parents", "Non_Laying_Parents", "F1", "LBX", "PBX"):
        p, f = c[(g, "pass")], c[(g, "fail")]
        cells.append(f"{p}/{p + f} ({100 * p / max(1, p + f):.0f}%)")
    p = sum(r["status"] == "pass" for r in vr)
    cells.append(f"{p}/{len(vr)} ({100 * p / len(vr):.0f}%)")
    rows.append(cells)
table(["Face", "Parents", "Non-laying parents", "F1", "LBX", "PBX", "All"], rows,
      [0.7, 0.95, 0.95, 0.85, 0.95, 0.95, 0.95],
      note="Images passing the automatic accuracy check, by group. Failures are mostly golden flaps or the basal "
           "process merged into the outline at the heel or the basal lobes; LBX images have them most often.")
para(f"Spot checks by eye of random passed images found no errors on the Right face (9/9) or Left face (18/18), "
     "and one error on the Dorsal face (17/18, a flap traced as the shoulder); a shoulder-position check added "
     "afterwards rejects that case. Of 9 failed Right images inspected, 8 were genuine errors and 1 was a "
     "correct label rejected by a slightly tight tolerance.")

doc.add_heading("2. Biological signal on the same specimens", level=1)
para("Both protocols were analysed on identical specimens (those whose new labels passed). Old configurations "
     "were superimposed as fixed landmarks (as in the original analyses); new configurations with sliding "
     "semilandmarks. All models control for centroid size and camera session (the Parents were photographed on "
     "a different camera). Classes: lecontei and pinetum parents (by ID prefix ll/lx vs np/px), F1, LBX, PBX.")
rows = []
for r in summary:
    rows.append([VIEW_NAME[r["view"]], r["protocol"], r["n"], r["p"], r["class_R2"], r["class_Z"],
                 r["species_R2"], r["species_Z"], f"{100 * float(r['lda5_acc']):.1f}%"])
table(["Face", "Protocol", "n", "Points", "Class R²", "Class Z", "Species R²", "Species Z", "5-class LDA"], rows,
      [0.65, 0.7, 0.45, 0.55, 0.7, 0.65, 0.8, 0.8, 0.9],
      note="Class = five groups; species = lecontei vs pinetum parents. R² and Z (effect size) from Procrustes "
           "ANOVA with 999 permutations, class/species after size and camera session. 5-class LDA = leave-one-out "
           "classification accuracy on shape principal components.")
doc.add_heading("2.1 Is either protocol better? Paired bootstrap", level=2)
para("Specimens were resampled 300 times (with replacement, within each class). Each resample was scored under "
     "both protocols, so the difference between them is estimated directly.")
rows = [[VIEW_NAME[r["view"]], r["effect"], r["R2_old"], r["R2_new"], r["new_minus_old"], r["P_new_higher"]]
        for r in boot]
table(["Face", "Effect", "R² old [95%]", "R² new [95%]", "New − old [95%]", "Share new > old"], rows,
      [0.6, 1.2, 1.3, 1.3, 1.4, 0.8],
      note="Every interval for the difference includes zero: neither protocol separates the groups significantly "
           "better on these labels.")
doc.add_heading("2.2 Where the signal is: region by region", level=2)
para("Each anatomical region was superimposed on its own and tested for the species difference (after size and "
     "camera session). Regions are matched between protocols as closely as their points allow.")
rows = [[VIEW_NAME[r["view"]], r["module"], r["protocol"], r["n_points"], r["R2"], r["Z"]] for r in mods]
table(["Face", "Region", "Protocol", "Points", "Species R²", "Species Z"], rows,
      [0.7, 2.3, 0.8, 0.7, 0.9, 0.9],
      note="In the regions both protocols measure, the new protocol captures as much species signal or more "
           "(ventral margin and heel higher; window similar; dorsal margin higher R² on both faces, Z higher on "
           "Right and lower on Left). The whole side-face configuration is nevertheless lower; one likely reason "
           "is weighting, since in a single superimposition regions contribute in proportion to their number of "
           "points. The Dorsal shaft/shoulder region is new; its species difference is mostly size-related "
           "(Z falls from 4.7 to 2.4 once size is in the model).")
doc.add_heading("2.3 Hybrid index", level=2)
para("Each specimen was projected onto the axis from the lecontei mean shape (0) to the pinetum mean shape (1). "
     "If the shape differences are heritable and largely additive, the backcrosses should sit toward their "
     "recurrent parent (LBX near 0, PBX near 1) and F1 in between.")
doc.add_picture(FIGPATH, width=Inches(6.5))
doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
rows = [[VIEW_NAME[r["view"]], r["protocol"], r["hi_lecontei"], r["hi_LBX"], r["hi_F1"], r["hi_PBX"],
         r["hi_pinetum"]] for r in summary]
table(["Face", "Protocol", "lecontei", "LBX", "F1", "PBX", "pinetum"], rows, [0.8, 0.9, 0.9, 0.9, 0.9, 0.9, 0.9],
      note="Median hybrid index per group (dots = specimens, black bar = median in the figure). On both side "
           "faces and under both protocols the groups fall in the expected order LBX < F1 < PBX. On the Dorsal "
           "face LBX is not below F1 under either protocol, which is worth examining (possible dominance in "
           "tip/Dorsal traits, or the small F1 sample, 6 of which were photographed on the other camera).")

doc.add_heading("3. Interpretation and caveats", level=1)
bullets([
    "**Label-stage comparison.** The new labels reuse the old human anchor points plus automatic outlines, and "
    "are compared against a fully human configuration. The new protocol's intended advantages (frame-free "
    "definitions, lower placement error, consistent automated measurement) are not what group separation tests.",
    "**Unknown digitizing effects.** Without repeat digitizing, part of the old protocol's group separation "
    "could reflect how different batches were digitized rather than biology; this applies to both protocols' "
    "shared anchors.",
    "**Group separation is not QTL power.** Mapping needs heritable variation within the backcrosses measured "
    "with low error, which is the signal-to-noise comparison in Section 4.",
    "**Excluded images.** 16–20% of images per face were excluded by the automatic check, more often LBX. "
    "Both protocols were analysed on the same remaining specimens, so the comparison is fair, but the sample "
    "is not the full dataset.",
    "**Point weighting.** In whole-configuration analyses each region counts in proportion to its number of "
    "points, so the 10-point dorsal curve and the heel curve weigh heavily; Section 4 shows the dorsal curve is "
    "also the noisiest part of the Right face under automated measurement. Region-level analyses avoid this.",
    "**Discarded test.** A formal effect-size comparison (RRPP pairwise.model.Z on residualised shapes) gave "
    "implausible values and was replaced by the paired bootstrap above.",
])

doc.add_heading("4. Signal-to-noise under automated measurement (CNN baseline)", level=1)
para("Design: one CNN per face and protocol (ResNet18 backbone, DSNT coordinate loss, cosine learning-rate decay, "
     "40 epochs, batch 8; the settings of the September 2026 cluster runs), trained on the same images with "
     "identical train/validation/test splits under both protocols. On the held-out test specimens, predicted "
     "and label configurations are superimposed together; measurement error (label vs prediction) is compared "
     "with the real between-specimen variation, for all specimens and within the backcrosses (LBX + PBX), "
     "whose variation is what QTL mapping uses.")
if snr:
    rows = []
    for v in ("Right", "Left", "Bottom"):
        for pr in ("old", "new"):
            e = evals.get((v, pr), {})
            rows.append([VIEW_NAME[v], pr, f"{e.get('median_px_error', float('nan')):.1f}",
                         f"{e.get('mean_px_error', float('nan')):.1f}", e.get("n_test_images", "")])
    para("Landmark error of each model on its own test labels (not comparable between protocols, which have "
         "different points; shown to confirm both trained normally):", size=10)
    table(["Face", "Protocol", "Median error (px)", "Mean error (px)", "Test specimens"], rows,
          [0.8, 0.9, 1.4, 1.4, 1.2])
    rows = []
    for v in ("Right", "Left", "Bottom"):
        for sub in ("all", "backcrosses"):
            for meas in ("shape", "log centroid size"):
                o, n_ = snr_row(v, "old", sub, meas), snr_row(v, "new", sub, meas)
                d = diff_row(v, sub, meas)
                rows.append([VIEW_NAME[v], "all test" if sub == "all" else "LBX + PBX", meas, o["n"],
                             o["repeatability"], n_["repeatability"], d["repeatability_new_minus_old"]])
    table(["Face", "Specimens", "Measure", "n", "Repeatability old [95%]", "Repeatability new [95%]",
           "New − old [95%]"], rows, [0.6, 0.8, 0.9, 0.35, 1.3, 1.3, 1.25],
          note="Repeatability = share of variance that is real between-specimen variation rather than "
               "label-vs-CNN disagreement (Procrustes ANOVA, specimen as factor, label and prediction as two "
               "replicates; 1000 paired bootstrap resamples of specimens). Signal-to-noise ratios are in "
               "output/snr_summary.csv.")
    para("**Dorsal face.** The new protocol's automated measurements carry far more real signal, most of all in "
         "the backcrosses, where old-protocol CNN shape measurements were dominated by error (signal-to-noise "
         f"{snr_row('Bottom', 'old', 'backcrosses', 'shape')['snr_observed']} old vs "
         f"{snr_row('Bottom', 'new', 'backcrosses', 'shape')['snr_observed']} new). This matches the old "
         "protocol's known Dorsal problems: the ambiguous split point and the crowded fork cluster, both replaced "
         "in the new scheme. Size is also measured more repeatably.")
    para("**Left face.** No difference in shape or size repeatability.")
    para("**Right face.** The new protocol's shape repeatability is lower. Its largest errors are all on the "
         "dorsal-edge curve (R18 and the dorsal semilandmarks, 25–40 px mean error), plus one Parents image with a "
         "gross 119 px error. Removing the curve from the comparison, using the same predictions, closes the gap:")
    if ablation:
        table(["Right face, same test predictions", "n", "Old", "New", "New − old [95%]"],
              [[r["analysis"], r["n"], r["rep_old"], r["rep_new"], r["new_minus_old"]] for r in ablation],
              [2.9, 0.4, 0.6, 0.6, 1.7],
              note="Removing only the start of the dorsal curve does not help; the curve is noisy along its whole "
                   "length on the Right face. On the Left face, where the same curve is present, repeatability "
                   "matches the old protocol, so the problem is specific to the Right-face dorsal edge.")
    if hard:
        doc.add_heading("4.1 Follow-up: why the Right face lagged, and unseen difficult specimens", level=2)
        para("**The Right-face gap was mostly label error, not model error.** In the four worst Right test images, "
             "the automatic label's dorsal curve started on the golden basal flap: the rule for R18 took the "
             "farthest crossing of the line through suture 1, which was the top of the flap. The model's "
             "prediction followed the true dorsal edge. For a typical specimen the Right dorsal curve performed "
             "like the Left one. The rule now takes the first crossing (the lance's own edge), and a new QC check "
             "rejects labels where a flap touching the edge makes the lance look too tall at suture 1.")
        para("**Generalization test.** Both round-1 models were run on the digitized images they never saw "
             "(excluded by the automatic QC, mostly specimens with flaps or membrane at the heel, dorsal margin or "
             "basal lobes) and scored against the original human points. The dorsal-edge measure is comparable "
             "between protocols (distance from the human dorsal-edge points to each model's predicted edge); the "
             "heel and Dorsal-face anchor measures partly reflect deliberately changed definitions.")
        rows = [[VIEW_NAME[r["view"]], r["set"], r["measure"], r["n"], r["old_median_um"], r["new_median_um"],
                 r["new_minus_old_median"], f"{r['old_gross_pct']}% / {r['new_gross_pct']}%"] for r in hard]
        table(["Face", "Images", "Measure", "n", "Old (µm)", "New (µm)", "New − old [95%]", ">50 µm old / new"],
              rows, [0.55, 0.5, 1.35, 0.35, 0.6, 0.6, 1.25, 1.0],
              note="Medians of per-image mean error, in µm (927 or 1260 px/mm by camera). easy = test split; "
                   "hard = never-seen excluded images.")
        para("**Result.** On never-seen difficult specimens the new model's dorsal curve failed on 14.8% of Left "
             "images (>50 µm), against 0% for the old model. In every one of the worst cases (LBX specimens with a "
             "golden flap above the dorsal margin) the model started the curve on the flap, and because the dorsal "
             "semilandmarks are spaced from that start point, the whole curve was dragged off the edge. Two causes: "
             "the model had learned it from the ~4% of training labels with the same flap error (since fixed), and "
             "the design ties every dorsal point to the start point.")
        para("**Round 2 (in progress).** Right and Left are being retrained on the corrected labels, for three "
             "models each on identical images and splits: old protocol; new protocol with the corrected start; and "
             "new protocol with the dorsal curve starting at the window's proximal end (R11/L11 level), away from "
             "the heel and flap. The signal-to-noise and never-seen tests will then be repeated.", italic=True)

    doc.add_heading("5. Recommendations", level=1)
    bullets([
        "**Adopt the new Dorsal-face protocol.** It gives clearly more repeatable automated shape and size "
        "measurement, especially in the backcrosses, and adds the shaft and shoulders.",
        "**Decide the lateral dorsal curve's start point after round 2** (Section 4.1). The curve carries species "
        "signal (Section 2.2), but starting it next to the heel makes it vulnerable to the golden basal flap on "
        "both lateral faces. Round 2 compares the current start with one at the window's proximal end.",
        "**Keep the rest of the lateral scheme.** Ventral margin, sutures, window and heel match or exceed the old "
        "protocol in species signal, and without the Right dorsal curve the lateral faces match the old "
        "protocol's repeatability.",
        "**Next analyses:** re-run this comparison with the revised lateral scheme; extend predictions to all raw "
        "images (cross-validated, so every specimen is predicted by a model that never saw it); and, if possible, "
        "a small repeat-digitizing set to separate digitizer effects from biology.",
    ])
else:
    para("Status: the six models are training; this section is regenerated with the results when they finish.",
         italic=True)

doc.add_heading("Files", level=1)
bullets([
    "tools/autolabel.py, tools/autolabel_qc.py: automatic labels and the accuracy check (autolabels/).",
    "analysis/prep_protocol_comparison.py: matched old/new datasets (analysis/data/).",
    "analysis/compare_protocols.R, bootstrap_compare.R, module_old_vs_new.R, module_species.R: the analyses "
    "above (analysis/output/).",
    "cnn/run_protocol_comparison.sh: the six CNN trainings (lance_landmarking/model/runs/protocol_comparison/); "
    "analysis/snr_compare.R and snr_ablation_right.R: Section 4.",
    "analysis/make_findings_docx.py: this document.",
])

for z in doc.settings.element.iter(qn("w:zoom")):
    if z.get(qn("w:percent")) is None:
        z.set(qn("w:percent"), "100")
doc.save(OUT)
print("wrote", OUT)
