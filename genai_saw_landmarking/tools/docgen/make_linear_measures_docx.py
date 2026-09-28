"""Generates genai_saw_landmarking/production/Saw_v12_Linear_Measures.docx: definitions of the linear
measures computed by production/saw_v12_morphometrics.R, with figures drawn on a real specimen.

Every figure is drawn from the CNN's v1.2 prediction for the example saw, using the same point numbers
and the same geometry as the R script (saw axis R1 -> R7, perpendicular distances to chords), so the
figures show exactly what the numbers measure. Rerun after any change to the R script's measures rather
than hand-editing the .docx.

usage (from repo root, project venv):
    python genai_saw_landmarking/tools/docgen/make_linear_measures_docx.py
"""
import csv
import sys
from pathlib import Path

import numpy as np
import tifffile
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from measure_figs import Fig, PALETTE  # noqa: E402

ROOT = HERE.parents[1]
PROD = ROOT / "production"
OUT = PROD / "Saw_v12_Linear_Measures.docx"
FIGDIR = ROOT / "figures" / "linear_measures"
EXAMPLE = "ag008_f10_r"  # N. lecontei, g0, virginia pine
KEY = list(csv.DictReader(open(PROD / "output" / "geomorph" / "landmark_key_v12.csv")))
ID = {r["id"]: int(r["number"]) for r in KEY}

# ----------------------------------------------------------------- example specimen (protocol frame px)
row = next(r for r in csv.DictReader(open(PROD / "output" / "predictions_px_saw.csv")) if r["key"] == EXAMPLE)
P = np.array([[float(row[f"x{k}"]), float(row[f"y{k}"])] for k in range(1, len(KEY) + 1)])
IMG = tifffile.imread(PROD / row["image"])
PPM = float(row["px_per_mm"])


def p(name):
    return P[ID[name] - 1]


V = {k: f"V{k}" for k in range(1, 8)}
R = {k: f"R{k}" for k in range(1, 8)}
D = {k: f"D{k}" for k in range(1, 8)}
# the same chains as saw_v12_morphometrics.R (1-based point numbers), as 0-based indices
VENTRAL = [n - 1 for n in [3, 26, 9, 27, 28, 4, 29, 10, 30, 31, 5, 32, 11, 33, 34, 6, 35, 36, 37, 7, 38, 39, 40, 8, 41, 42, 43, 44, 45, 46, 1]]
RACHIS = [n - 1 for n in [12, 47, 13, 48, 14, 49, 15, 50, 16, 51, 17, 52, 18]]

FIGDIR.mkdir(parents=True, exist_ok=True)
C = PALETTE


def base(crop_pts=None, width=1800, pad=90):
    f = Fig(IMG, crop_pts if crop_pts is not None else P, width=width, pad=pad)
    f.points(P, color=(90, 90, 90), r=3)
    return f


# Figure 1: landmark key
f = Fig(IMG, P, width=1800, pad=90)
f.poly(P[VENTRAL], C[1], width=2); f.poly(P[RACHIS], C[2], width=2)
for n in range(25, 52):
    f.points(P[[n]], color=(240, 240, 240), r=4, outline=(0, 0, 0))
    f.text(P[n], str(n + 1), (60, 60, 60), size=16, dx=6, dy=-18)
for r_ in KEY[:25]:
    q = P[int(r_["number"]) - 1]
    f.points(q[None], color=(220, 30, 30), r=6, outline=(0, 0, 0))
    up = r_["id"][0] in "VTS"
    f.text(q, f'{r_["number"]} {r_["id"]}', (0, 0, 0), size=22, dx=-20, dy=-34 if up else 12)
f.save(FIGDIR / "saw_fig1_key.jpg")

# Figure 2: whole-saw measures
f = base()
f.line(p("S01"), p("V1"), C[0], "Saw_length")
f.poly(P[VENTRAL], C[1], "Ventral_arc_length", label_at=0.35)
f.poly(P[RACHIS], C[2], "Rachis_arc_length", label_at=0.5, label_dy=26)
f.line(p("R1"), p("R7"), C[3], "Rachis_chord", dashed=True, label_t=0.3, label_dy=-30)
rc = P[RACHIS]; u = (p("R7") - p("R1")) / np.linalg.norm(p("R7") - p("R1")); nrm = np.array([-u[1], u[0]])
dev = (rc - p("R1")) @ nrm; j = int(np.argmax(np.abs(dev))); foot = rc[j] - dev[j] * nrm
f.line(rc[j], foot, C[4], "sagitta", width=5)
f.line(p("V7"), p("S01"), C[5], "Tip_length_ventral", label_dy=-30)
f.line(p("R7"), p("S01"), C[6], "Tip_length_rachis", label_dy=24)
f.line(p("D1"), p("D7"), C[7], "Dorsal_span", label_t=0.6, label_dy=24)
f.save(FIGDIR / "saw_fig2_whole.jpg")

# Figure 3: annulus 3 (the same for annuli 1-7)
k = 3
f = base()
f.line(p(V[k]), p(R[k]), C[0], f"Ann{k}_ventral", label_dx=12)
f.line(p(R[k]), p(D[k]), C[1], f"Ann{k}_dorsal", label_dx=12)
band = p(D[k]) - p(V[k]); band = band / np.linalg.norm(band)
off = np.array([band[1], -band[0]]) * 45  # beside the band, towards the apex
f.line(p(V[k]) + off, p(D[k]) + off, C[2], f"Ann{k}_length", label_dx=-190)
f.line(p("R1"), p("R7"), (120, 120, 120), "saw axis R1-R7", dashed=True, label_t=0.15, label_dy=-30)
ax_end = p(V[k]) + u * 180
f.line(p(V[k]), ax_end, C[3], None, dashed=True)
f.angle(p(V[k]), ax_end, p(D[k]), C[3], f"Ann{k}_angle")
f.save(FIGDIR / "saw_fig3_annulus.jpg")

# Figure 4: spacing between annuli 3 and 4 (the same for every neighbouring pair 1-2 ... 6-7)
f = base()
f.line(p("V3"), p("V4"), C[0], "Ann3_4_ventral", label_dy=20)
f.line(p("R3"), p("R4"), C[1], "Ann3_4_rachis", label_dy=22)
f.line(p("D3"), p("D4"), C[2], "Ann3_4_dorsal", label_dy=-32)
f.save(FIGDIR / "saw_fig4_spacing.jpg")

# Figure 5: serrula 2 length and notch depth (zoomed)
notch = [26, 27]  # semilandmarks 27, 28 (0-based 26, 27) between T2 and V3
zoom = np.array([p("V2"), p("V3"), p("T2"), P[26], P[27]])
f = base(crop_pts=zoom, width=1500, pad=70)
f.poly(P[VENTRAL], (160, 160, 160), width=2)
f.line(p("V2"), p("T2"), C[0], "Serrula2_length", label_dy=-36)
f.line(p("T2"), p("V3"), C[1], "chord T2-V3", dashed=True, label_dy=24)
ch = p("V3") - p("T2"); ch = ch / np.linalg.norm(ch); cn = np.array([-ch[1], ch[0]])
d = [(P[i] - p("T2")) @ cn for i in notch]; j = notch[int(np.argmax(np.abs(d)))]
foot = P[j] - ((P[j] - p("T2")) @ cn) * cn
f.line(P[j], foot, C[4], "Serrula2_notch_depth", width=5, label_dx=10)
for nme in ("V2", "T2", "V3"):
    f.text(p(nme), nme, (0, 0, 0), size=26, dx=-14, dy=-40)
f.save(FIGDIR / "saw_fig5_serrula.jpg")

# ------------------------------------------------------------------------------------------ document
doc = Document()
sec = doc.sections[0]
sec.page_width, sec.page_height = Inches(8.5), Inches(11)
for side in ("left_margin", "right_margin", "top_margin", "bottom_margin"):
    setattr(sec, side, Inches(1))
normal = doc.styles["Normal"]
normal.font.name = "Calibri"; normal.element.rPr.rFonts.set(qn("w:eastAsia"), "Calibri"); normal.font.size = Pt(11)
for lvl in (1, 2):
    st = doc.styles[f"Heading {lvl}"]
    st.font.name, st.font.size, st.font.bold = "Calibri", Pt(13 if lvl == 1 else 12), True
    st.font.color.rgb = RGBColor(0, 0, 0); st.element.rPr.rFonts.set(qn("w:eastAsia"), "Calibri")


def para(text, bold=False, italic=False, size=None, align=None):
    q = doc.add_paragraph()
    r_ = q.add_run(text); r_.bold, r_.italic = bold, italic
    if size:
        r_.font.size = Pt(size)
    if align:
        q.alignment = align
    return q


def shade(cell, hex_fill):
    tcPr = cell._tc.get_or_add_tcPr()
    s = OxmlElement("w:shd"); s.set(qn("w:val"), "clear"); s.set(qn("w:color"), "auto"); s.set(qn("w:fill"), hex_fill)
    tcPr.append(s)


def table(header, rows, widths):
    t = doc.add_table(rows=1, cols=len(header)); t.style = "Table Grid"
    for i, h in enumerate(header):
        c = t.rows[0].cells[i]; c.text = h; shade(c, "D9D9D9")
        c.paragraphs[0].runs[0].bold = True
    for rw in rows:
        cells = t.add_row().cells
        for i, v in enumerate(rw):
            cells[i].text = v
    for rr in t.rows:
        for i, w in enumerate(widths):
            rr.cells[i].width = Inches(w)
            for q in rr.cells[i].paragraphs:
                for run in q.runs:
                    run.font.size = Pt(9.5)
    doc.add_paragraph()
    return t


def picture(path, caption, width=6.5):
    doc.add_picture(str(path), width=Inches(width))
    doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
    para(caption, italic=True, size=9.5)


def pt(name):
    return f"{name} ({ID[name]})"


H = ["Measure (column)", "Points", "Definition"]
W = [1.75, 1.45, 3.3]

doc.add_heading("Saw Protocol v1.2: Linear Measurements", level=0)
para("Definitions of the linear measures written by production/saw_v12_morphometrics.R (function saw_measures) "
     "into PRIME_Saw_Pheno_v12.csv, one row per female. Each measure is computed from the 52-point configuration "
     "in Saw_v12_XY.csv.")
for t_ in [
    "Units: millimetres, from each image's own scale bar. Angles are in degrees.",
    "Orientation (protocol frame): apex left, teeth (serrulae) up, annulus 1 on the right. Point names are anatomical: V = ventral (toothed) end of an annulus, T = serrula tip, R = annulus × ventral margin of the rachis, D = dorsal end of an annulus.",
    "Point numbers follow landmark_key_v12.csv. They are given in brackets after each point name, e.g. V3 (4).",
    "Distances are straight lines between points unless the definition says 'along' a curve (sum of the segments through the curve's points).",
    f"Figures: CNN landmarks of the N. lecontei saw {EXAMPLE.upper()} (g0, virginia pine). The measures are drawn exactly as the script computes them.",
]:
    doc.add_paragraph(t_, style="List Bullet")

doc.add_heading("Landmarks", level=1)
picture(FIGDIR / "saw_fig1_key.jpg", "Figure 1. The 52 points. Red: the 25 anchors (number and name). White: sliding semilandmarks "
        "(26–46 on the toothed edge, blue line; 47–52 on the rachis, green line).")
table(["Points", "Numbers", "What they are"], [
    ["S01", "1", "Apex of the saw"],
    ["V1–V7", "2–8", "Ventral end of annuli 1–7 (V2–V7 on the toothed edge; V1 at the end of the band)"],
    ["T2–T4", "9–11", "Tips of serrulae 2–4"],
    ["R1–R7", "12–18", "Where annuli 1–7 cross the ventral margin of the rachis"],
    ["D1–D7", "19–25", "Dorsal ends of annuli 1–7 (D1–D2 on the dorsal margin of the rachis)"],
    ["semilandmarks", "26–46", "Toothed (ventral) edge, V2 → apex"],
    ["semilandmarks", "47–52", "Ventral margin of the rachis, R1 → R7"],
], [1.2, 0.9, 4.4])

doc.add_heading("Whole saw", level=1)
picture(FIGDIR / "saw_fig2_whole.jpg", "Figure 2. Whole-saw measures.")
table(H, [
    ["Saw_length", f"{pt('S01')}–{pt('V1')}", "Apex to the ventral end of annulus 1. Replaces the old BottomLengthLM (old points 15–1)."],
    ["Ventral_arc_length", "V2 (3) … S01 (1), along points 26–46", "Length of the toothed edge, following every serrula and notch from annulus 2 to the apex."],
    ["Rachis_arc_length", "R1 (12) … R7 (18), along 47–52", "Length of the rachis (the side of the saw that slides on the lance) from annulus 1 to annulus 7."],
    ["Rachis_chord", f"{pt('R1')}–{pt('R7')}", "Straight-line length of the rachis, annulus 1 to 7. Also defines the saw axis used for angles."],
    ["Rachis_sagitta", "rachis points vs chord R1–R7", "Curvature of the rachis: the largest perpendicular distance of the rachis curve from its chord, divided by the chord (unitless; larger = more curved)."],
    ["Tip_length_ventral", f"{pt('V7')}–{pt('S01')}", "Annulus 7 (ventral end) to the apex: the distal, crowded tip region."],
    ["Tip_length_rachis", f"{pt('R7')}–{pt('S01')}", "Annulus 7 on the rachis to the apex. Replaces the old DistAnn7_tiptopLM."],
    ["Dorsal_span", f"{pt('D1')}–{pt('D7')}", "Distance between the dorsal ends of annuli 1 and 7."],
], W)

doc.add_heading("Annuli (k = 1–7)", level=1)
picture(FIGDIR / "saw_fig3_annulus.jpg", "Figure 3. Measures of one annulus, drawn for annulus 3 (the same four measures are computed for annuli 1–7). "
        "Ann3_length is drawn offset to the left of the band so it does not hide the other two.")
table(H, [
    ["Annk_length", "Vk–Dk", "Full length of annulus k, ventral end to dorsal end. Replaces the old AnnkLM."],
    ["Annk_ventral", "Vk–Rk", "Blade depth below the rachis at annulus k: ventral end to the rachis."],
    ["Annk_dorsal", "Rk–Dk", "Part of annulus k above the rachis ventral margin (rachis and dorsal strip)."],
    ["Annk_angle", "Vk→Dk vs R1→R7", "Inclination of annulus k to the saw axis (R1 → R7), 0–90°. 90° = perpendicular to the rachis."],
], W)
para("Point numbers: V1–V7 = 2–8, R1–R7 = 12–18, D1–D7 = 19–25 (for annulus k: V = k+1, R = k+11, D = k+18).", size=10)

doc.add_heading("Spacing between annuli (k = 1–6)", level=1)
picture(FIGDIR / "saw_fig4_spacing.jpg", "Figure 4. Spacing between neighbouring annuli, drawn for annuli 3 and 4 (computed for every pair 1–2 … 6–7).")
table(H, [
    ["Annk_k+1_ventral", "Vk–Vk+1", "Spacing on the toothed edge. Replaces the old DistAnnk_k+1botLM."],
    ["Annk_k+1_rachis", "Rk–Rk+1", "Spacing along the rachis. Replaces the old DistAnnk_k+1topLM (old points 16–22 were the rachis crossings)."],
    ["Annk_k+1_dorsal", "Dk–Dk+1", "Spacing of the dorsal band ends."],
], W)

doc.add_heading("Serrulae (teeth), k = 2–4", level=1)
picture(FIGDIR / "saw_fig5_serrula.jpg", "Figure 5. Serrula 2 (the same for serrulae 3 and 4), enlarged. The grey line is the traced toothed edge.")
table(H, [
    ["Serrulak_length", "Vk–Tk", "From the base of serrula k (ventral end of annulus k) to its tip. Replaces the old Tooth1–3LM (serrulae 2–4)."],
    ["Serrulak_notch_depth", "semilandmarks between Tk and Vk+1 vs chord Tk–Vk+1",
     "Depth of the notch after serrula k: the larger perpendicular distance of the two toothed-edge semilandmarks between the tip Tk and the next annulus Vk+1 "
     "(27–28 for k = 2, 30–31 for k = 3, 33–34 for k = 4) from the straight line Tk–Vk+1. Replaces the old notch points 4 and 7."],
], W)

doc.add_heading("Notes", level=1)
for t_ in [
    "Old-protocol measures without a v1.2 equivalent: TopLengthLM and RootTipLM used old points 25 and 32, which were dropped (25 was the least repeatable point; 32 is not the same annulus in the two species). Tip measures beyond annulus 7 (old annuli 8–9) are not computed, because the number of distal annuli differs between species.",
    "Shape is analysed separately, by Procrustes superimposition of all 52 points with the semilandmarks sliding. The linear measures are for univariate models and comparison with the old tables.",
    "Size: every measure scales with saw size. For size-corrected comparisons, include centroid_size or body_length in the model, as the script does for the host models.",
    "Only QC-passed saws are used, one saw per female (the left if both were imaged). Side (left/right saw) can be added to the models as a nuisance term.",
]:
    doc.add_paragraph(t_, style="List Bullet")
para(f"Generated by genai_saw_landmarking/tools/docgen/make_linear_measures_docx.py. Example scale: {PPM:.1f} px/mm.", italic=True, size=9)
zoom = doc.settings.element.find(qn("w:zoom"))  # python-docx's template omits the required w:percent
if zoom is not None and zoom.get(qn("w:percent")) is None:
    zoom.set(qn("w:percent"), "100")
doc.save(OUT)
print("wrote", OUT)
