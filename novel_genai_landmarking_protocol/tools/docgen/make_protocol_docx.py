"""Generates novel_genai_landmarking_protocol/Lance_Imaging_Morphometrics_v3.docx.

The human-executable version of Lance_Landmarking_Protocol.md (v1.3), laid out
like Lance_Imaging_Morphometrics_v2.docx (rehydration and imaging steps are
carried over from v2 unchanged; the morphometrics section is new). Rerun this
after any protocol change rather than hand-editing the .docx.

Point definitions and the old->new mapping are read from landmark_schema.json
(itself generated from tools/scheme.py), so the tables can't drift from the code.

usage (from repo root, project venv):
    python novel_genai_landmarking_protocol/tools/docgen/make_protocol_docx.py
"""
import json
import zipfile
from datetime import date
from io import BytesIO
from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "Lance_Imaging_Morphometrics_v3.docx"
OLD = ROOT / "Landmarked_Images" / "Lance_Imaging_Morphometrics_v2.docx"
FIG = ROOT / "figures"
SCHEMA = json.load(open(ROOT / "landmark_schema.json"))
FIG_SPECIMEN = "ll280xll284-1"  # N. lecontei parent used for the reference figures

doc = Document()
sec = doc.sections[0]
sec.page_width, sec.page_height = Inches(8.5), Inches(11)
for side in ("left_margin", "right_margin", "top_margin", "bottom_margin"):
    setattr(sec, side, Inches(1))
normal = doc.styles["Normal"]
normal.font.name = "Calibri"
normal.element.rPr.rFonts.set(qn("w:eastAsia"), "Calibri")
normal.font.size = Pt(12)
for lvl, size in ((1, 12), (2, 12)):
    st = doc.styles[f"Heading {lvl}"]
    st.font.name, st.font.size, st.font.bold = "Calibri", Pt(size), True
    st.font.color.rgb = RGBColor(0, 0, 0)
    st.element.rPr.rFonts.set(qn("w:eastAsia"), "Calibri")
    st.font.italic = lvl == 2
    st.paragraph_format.space_before = Pt(12)
    st.paragraph_format.space_after = Pt(4)

# ------------------------------------------------------------------ numbering
# one decimal abstract list; every numbered list gets its own w:num so it restarts at 1
numbering = doc.part.numbering_part.element
ABS_ID = 900
absn = OxmlElement("w:abstractNum")
absn.set(qn("w:abstractNumId"), str(ABS_ID))
for ilvl, fmt, txt in ((0, "decimal", "%1."), (1, "lowerLetter", "%2.")):
    lvl = OxmlElement("w:lvl")
    lvl.set(qn("w:ilvl"), str(ilvl))
    for tag, val in (("w:start", "1"), ("w:numFmt", fmt), ("w:lvlText", txt), ("w:lvlJc", "left")):
        e = OxmlElement(tag)
        e.set(qn("w:val"), val)
        lvl.append(e)
    ppr = OxmlElement("w:pPr")
    ind = OxmlElement("w:ind")
    ind.set(qn("w:left"), str(720 * (ilvl + 1)))
    ind.set(qn("w:hanging"), "360")
    ppr.append(ind)
    lvl.append(ppr)
    absn.append(lvl)
numbering.insert(0, absn)
_num_counter = [900]


def new_list():
    _num_counter[0] += 1
    num = OxmlElement("w:num")
    num.set(qn("w:numId"), str(_num_counter[0]))
    a = OxmlElement("w:abstractNumId")
    a.set(qn("w:val"), str(ABS_ID))
    num.append(a)
    ov = OxmlElement("w:lvlOverride")
    ov.set(qn("w:ilvl"), "0")
    so = OxmlElement("w:startOverride")
    so.set(qn("w:val"), "1")
    ov.append(so)
    num.append(ov)
    numbering.append(num)
    return _num_counter[0]


def add_runs(p, text):
    """**bold** and *italic* inline markup."""
    import re
    for part in re.split(r"(\*\*[^*]+\*\*|\*[^*]+\*)", text):
        if part.startswith("**"):
            p.add_run(part[2:-2]).bold = True
        elif part.startswith("*") and len(part) > 1:
            p.add_run(part[1:-1]).italic = True
        elif part:
            p.add_run(part)
    return p


def steps(items, level=0):
    nid = new_list()
    for it in items:
        sub = None
        if isinstance(it, tuple):
            it, sub = it
        p = doc.add_paragraph(style="List Paragraph")
        pr = p._p.get_or_add_pPr()
        numpr = OxmlElement("w:numPr")
        il = OxmlElement("w:ilvl")
        il.set(qn("w:val"), str(level))
        ni = OxmlElement("w:numId")
        ni.set(qn("w:val"), str(nid))
        numpr.append(il)
        numpr.append(ni)
        pr.append(numpr)
        add_runs(p, it)
        if sub:
            for s in sub:
                q = doc.add_paragraph(style="List Paragraph")
                q.paragraph_format.left_indent = Inches(1.0)
                add_runs(q, "– " + s)


def para(text, bold=False, italic=False, size=None, align=None):
    p = doc.add_paragraph()
    add_runs(p, text)
    for r in p.runs:
        if bold:
            r.bold = True
        if italic:
            r.italic = True
        if size:
            r.font.size = Pt(size)
    if align:
        p.alignment = align
    return p


def shade(cell, hex_fill):
    tcpr = cell._tc.get_or_add_tcPr()
    sh = OxmlElement("w:shd")
    sh.set(qn("w:val"), "clear")
    sh.set(qn("w:color"), "auto")
    sh.set(qn("w:fill"), hex_fill)
    tcpr.append(sh)


def table(header, rows, widths):
    t = doc.add_table(rows=1, cols=len(header))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, h in enumerate(header):
        c = t.rows[0].cells[i]
        c.text = ""
        c.paragraphs[0].add_run(h).bold = True
        shade(c, "D9E2F3")
    for r in rows:
        cells = t.add_row().cells
        for i, v in enumerate(r):
            cells[i].text = ""
            add_runs(cells[i].paragraphs[0], str(v))
    for row in t.rows:
        for i, w in enumerate(widths):
            row.cells[i].width = Inches(w)
            for p in row.cells[i].paragraphs:
                for run in p.runs:
                    run.font.size = Pt(10)
    doc.add_paragraph()
    return t


def picture(path, width=6.5, caption=None):
    doc.add_picture(str(path), width=Inches(width))
    doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
    if caption:
        para(caption, italic=True, size=10, align=WD_ALIGN_PARAGRAPH.CENTER)


def old_image(name):
    with zipfile.ZipFile(OLD) as z:
        return BytesIO(z.read(f"media/{name}"))


# ------------------------------------------------------------------ title
para("Lance Imaging & Morphometrics v3", bold=True, size=14)
para(f"Landmark + semilandmark protocol. Generated {date.today().isoformat()} from "
     "Lance_Landmarking_Protocol.md (protocol v1.3). Rehydration and imaging are unchanged from v2; "
     "Lance Morphometrics is new and replaces the v2 multipoint landmarking.", italic=True, size=10)

# ------------------------------------------------------------------ rehydration (from v2)
doc.add_heading("Lance Rehydration", level=1)
steps([
    "Grab vial with Lance in 100% ethanol",
    "Transfer lance from vial of 100% ethanol into a vial of 75% ethanol and let it acclimate for 5 minutes",
    "After acclimation period 1 is over, transfer lance from vial of 75% ethanol into a vial of 50% ethanol and let it acclimate for 5 minutes",
    "After acclimation period 2, transfer lance from vial of 50% ethanol into a vial of 25% ethanol and let it acclimate for 5 minutes",
    "After acclimation period 3 is over transfer lance from vial of 25% ethanol into a vial of 10x PBS for lance to be imaged.",
])

# ------------------------------------------------------------------ imaging (from v2)
doc.add_heading("Lance Imaging", level=1)
steps([
    "Turn on camera, fiber-light, and 4k monitor.",
    "Set camera magnification to 5x.",
    "Right click and select “Set Scale” from the menu.",
    "Select “Nikon 5x”.",
    "Right click and select “Scale Bar” from the menu to add a scale bar to the image. **The scale bar must stay in the saved image: it calibrates each image during morphometrics.**",
    "Orient the lance for imaging (see below for guidelines pertaining to each side).",
    "If needed, you can digitally zoom by moving the mouse to the right of the screen and click on the “Zoom in” Icon.",
    "When you are ready to capture the image, move the mouse to the right of the screen and click the “Freeze” icon on the bottom.",
    "Right click and select “Text”.",
    "Rapidly click the screen until a text box appears. Click in the box and type the ID of the lance being measured.",
    "Drag this to an appropriate place near the lance.",
    "Move the mouse to the top right of the screen and click the “Capture” icon. Right click and select “exit” when done.",
    "At the end of imaging, remove the USB and transfer it to a computer of your choice.",
    "Rename each image with its ID (see below for guidelines pertaining to each side) and upload the images to SharePoint.",
])
doc.add_heading("Imaging the “Right” Face", level=2)
steps([
    "Orient the lance such that the tip is facing to the right and the sclerotized (darkened) edge is facing downward.",
    "The tip of the other side of the lance should not be visible.",
    "Ensure that the top edge of the tip is flat and not slanted.",
    "The bottom middle suture should not be visible.",
    "The entire lance should be in sharp focus. If it is not, then it should be reoriented accordingly.",
])
doc.add_picture(old_image("image4.png"), width=Inches(4.5))
doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
para("Reference image for a right-facing lance that is correctly oriented.", italic=True, size=10,
     align=WD_ALIGN_PARAGRAPH.CENTER)
doc.add_heading("Imaging the “Left” Face", level=2)
steps([
    "Orient the lance such that the tip is facing to the left and the sclerotized edge is facing downward.",
    "The tip of the other side should be visible but ensure that both tips are level with each other.",
    "The bottom middle suture should not be visible.",
    "The entire lance should be in sharp focus. If it is not, then it should be reoriented accordingly.",
])
doc.add_picture(old_image("image5.png"), width=Inches(4.5))
doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
para("Reference image for a left-facing lance that is correctly oriented.", italic=True, size=10,
     align=WD_ALIGN_PARAGRAPH.CENTER)
doc.add_picture(old_image("image6.png"), width=Inches(3.0))
doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
para("An incorrectly oriented left-facing lance where the asymmetrical sides are not aligned properly.",
     italic=True, size=10, align=WD_ALIGN_PARAGRAPH.CENTER)
doc.add_heading("Imaging the Dorsal Face", level=2)
steps([
    "Orient the lance such that it is downward facing, and they are facing to the right.",
    "The tips of both the short and long side should be visible.",
    "The bottom middle suture should be a straight line.",
    "The entire lance should be in sharp focus. If it is not, then it should be reoriented accordingly. "
    "**The whole structure is now measured, so check that the proximal end (the V-shaped notch between the two "
    "basal lobes) and the lobes' outer margins are in focus, not only the tips.**",
])
doc.add_picture(old_image("image7.png"), width=Inches(4.0))
doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
para("Reference image where the downward-facing lance is correctly oriented.", italic=True, size=10,
     align=WD_ALIGN_PARAGRAPH.CENTER)
para("Save files as “.tif”:")
steps([
    "“SampleID_R” for right-facing lances",
    "“SampleID_L” for left-facing images",
    "“SampleID_B” for downward-facing images (images of the dorsal face)",
])

# ------------------------------------------------------------------ morphometrics (new)
doc.add_page_break()
doc.add_heading("Lance Morphometrics", level=1)
para("Each image gets three kinds of points:")
steps([
    "**Anchors** (red dots in the figures): anatomical points you click with the Multi-point tool, in a fixed order. "
    "Right 17, Left 17, Dorsal 13.",
    "**Curves** (blue lines): margins you trace with the Segmented Line tool, from one anchor to another. "
    "You only trace the edge. **Never try to space points evenly by eye**: the software places the evenly spaced "
    "semilandmarks (white dots) on your trace afterwards.",
    "**Computed points** (purple diamonds): R18, L18 and B14. **You never click these**; the software works them out "
    "from your anchors and traces.",
])
para("For each image you save one ROI set (SampleID_R_ROI.zip, SampleID_L_ROI.zip or SampleID_B_ROI.zip) and fill "
     "one row of the annotation sheet (annotation_sheet_template.csv).")

doc.add_heading("One-time setup in Fiji/ImageJ", level=2)
steps([
    "Use Fiji (ImageJ).",
    "Double-click the Multi-point tool icon and set: Type **Hybrid**, Color **Yellow**, Size **Small**, and tick "
    "**Label points** so each click shows its number. Untick “Add to ROI Manager” and “Measure”.",
    "Double-click the Segmented Line tool icon and set the line width to 1.",
    "Open the ROI Manager: Analyze › Tools › ROI Manager.",
])

doc.add_heading("Steps for every image", level=2)
steps([
    "Open the **raw** TIFF (from Raw_Images), never a previously landmarked _MARK file.",
    ("**Calibrate from the scale bar.** Use the Straight Line tool to draw a line exactly along the scale bar, end to "
     "end. Analyze › Set Scale: Known distance = the bar's length (1 mm), Unit = mm, **Global unticked**. Write the "
     "“Distance in pixels” into the px_per_mm column of the sheet.",
     ["If an image has no scale bar, write the session value instead: 927 px/mm for 3840 × 2160 images, "
      "1260 px/mm for 2560 × 1920 images."]),
    "Empty the ROI Manager: select all entries and Delete.",
    ("**Click the anchors.** Select the Multi-point tool and click the anchors in the order in the table for that face. "
     "Zoom to at least 200% (Ctrl +) for each point.",
     ["To move a misplaced point, drag it. Do not delete points (Alt-click): deleting renumbers everything after it.",
      "If a point cannot be seen (hidden by debris, damaged, out of focus), still click your best estimate so the "
      "numbering stays correct, and write its ID (e.g. B12) in the flagged_points column. The analysis treats "
      "flagged points as missing rather than trusting the estimate."]),
    "Press **T** to add the anchors to the ROI Manager, then Rename… it to **anchors**.",
    ("**Trace the curves**, one at a time, in the order in the curve table. For each: select the Segmented Line "
     "tool; click once on the starting anchor; click along the margin every 20–40 pixels (closer where it bends); "
     "double-click on the ending anchor. Press **T** and Rename… it to the curve's name (e.g. R.heel).",
     ["Follow the edge of the amber/dark sclerotized cuticle, not pale membrane, and not rods or flaps attached to "
      "the lance (see Rules).",
      "Starting or stopping a little past the anchor is fine; the software trims each trace at its anchors.",
      "Keep the ROI Manager order: anchors first, then the curves in table order."]),
    "Tick **Show All** in the ROI Manager and compare against the reference figure for that face.",
    "**Save**: ROI Manager › More › Save… as SampleID_R_ROI.zip (or _L_ / _B_), in the same folder layout as the images.",
    "Fill in the annotation sheet row (columns described at the end of this section).",
])

VIEWS = SCHEMA["views"]


def anchor_rows(view, where):
    rows = []
    click = 0
    for p in VIEWS[view]["points"]:
        if p["role"] != "anchor":
            continue
        click += 1
        old = p.get("old_protocol_point")
        rows.append((click, p["id"], where[p["id"]], old if old else "new"))
    return rows


RIGHT_WHERE = {
    "R01": "**Apex**: the very tip of the lance.",
    "R02": "**Heel–ventral junction**: the proximal end of the dark sclerotized ventral edge, where it meets the heel.",
    "R03": "**Proximal heel notch**: the deepest point of the notch in the proximal (back) edge, between the heel and "
           "the basal process above it.",
    "R04": "**Suture 1, ventral end**: where the first suture from the heel meets the ventral edge.",
    "R05": "Suture 2, ventral end.", "R06": "Suture 3, ventral end.", "R07": "Suture 4, ventral end.",
    "R08": "Suture 5, ventral end.", "R09": "Suture 6, ventral end.", "R10": "Suture 7, ventral end.",
    "R11": "**Window, proximal end**: the most proximal point of the upper edge of the pale cuticular window.",
    "R12": "**Suture 2, dorsal end**: where suture 2 meets the upper edge of the window.",
    "R13": "Suture 3, dorsal end.", "R14": "Suture 4, dorsal end.", "R15": "Suture 5, dorsal end.",
    "R16": "Suture 6, dorsal end.",
    "R17": "**Window, distal end**: the most distal point of the upper edge of the window.",
}
LEFT_WHERE = {k.replace("R", "L"): v for k, v in RIGHT_WHERE.items() if k not in ("R10", "R01")}
LEFT_WHERE.update({
    "L01": "**Short-half apex**: the tip of the short half. In this view the long half's tip sticks out past it, so "
           "L01 is **inside** the outline, not the tip of the silhouette.",
    "L10": "**Ventral split point**: the last point on the ventral edge before the edges of the two halves separate.",
})
BOTTOM_WHERE = {
    "B01": "**Long-half apex**: the tip of the longer half.",
    "B02": "**Short-half apex**: the tip of the shorter half.",
    "B03": "**Long half, suture 1 from the apex**: where the most distal suture meets the long half's outer edge.",
    "B04": "Long half, suture 2 from the apex, outer end.",
    "B05": "Long half, suture 3 from the apex, outer end.",
    "B06": "Long half, suture 4 from the apex, outer end.",
    "B07": "**Short half, suture 1 from the apex**, outer end.",
    "B08": "Short half, suture 2 from the apex, outer end.",
    "B09": "Short half, suture 3 from the apex, outer end.",
    "B10": "Short half, suture 4 from the apex, outer end.",
    "B11": "**Median basal notch**: the deepest point of the V-shaped notch in the proximal end, between the two "
           "basal lobes.",
    "B12": "**Long-half shoulder**: where the long half's outer edge begins to curve outward into the basal lobe. Lay "
           "a straight edge (e.g. the Straight Line tool) against the outer edge so it touches the shaft edge and the "
           "front of the lobe; B12 is the edge point farthest from it.",
    "B13": "**Short-half shoulder**: the same on the short half.",
}

doc.add_heading("Right face (long half)", level=2)
picture(FIG / f"protocol_Right_{FIG_SPECIMEN}.jpg", caption="Right face (N. lecontei parent LL280xLL284-1). Red = anchors, "
        "white = semilandmarks placed by the software, purple = computed point R18.")
para("Anchors: click in this order (17 clicks).", bold=True)
table(["Click", "ID", "Where", "Old #"], anchor_rows("Right", RIGHT_WHERE), [0.5, 0.6, 4.6, 0.8])
para("Curves: trace in this order.", bold=True)
table(["Order", "Name", "Trace", "Points"], [
    (1, "R.heel", "From R03 down the proximal (back) edge of the heel to R02.", 4),
    (2, "R.vbase", "From R02 along the ventral edge to R04.", 2),
    (3, "R.vdist", "From R10 along the ventral edge to the apex R01.", 4),
    (4, "R.dorsal", "From the top of the heel, anywhere behind the point directly above R04, along the upper "
                    "(dorsal) edge to R01. The software starts the curve at R18, the point on this edge straight "
                    "above R04.", 10),
    (5, "R.window", "From R11 along the upper edge of the pale window to R17, passing through R12–R16 and following "
                    "the scalloped edge between them.", 4),
], [0.6, 0.9, 4.3, 0.7])
para("Count every suture you can see meeting the ventral edge from heel to tip, and write the number in "
     "sutures_visible.")

doc.add_heading("Left face (short half)", level=2)
picture(FIG / f"protocol_Left_{FIG_SPECIMEN}.jpg", caption="Left face. Same scheme as Right, with 6 anchored sutures and the "
        "ventral split point L10.")
para("Anchors: click in this order (17 clicks).", bold=True)
table(["Click", "ID", "Where", "Old #"], anchor_rows("Left", LEFT_WHERE), [0.5, 0.6, 4.6, 0.8])
para("Curves: trace in this order.", bold=True)
table(["Order", "Name", "Trace", "Points"], [
    (1, "L.heel", "From L03 down the proximal edge of the heel to L02.", 4),
    (2, "L.vbase", "From L02 along the ventral edge to L04.", 2),
    (3, "L.vdist", "From L10 along the **short half's own** ventral edge to L01. This edge runs inside the "
                   "outline; the long half's tip forms the outline here.", 2),
    (4, "L.dorsal", "From the top of the heel, behind the point directly above L04, along the dorsal edge to L01. "
                    "The software starts the curve at L18.", 10),
    (5, "L.window", "From L11 along the upper edge of the pale window to L17, through L12–L16.", 4),
], [0.6, 0.9, 4.3, 0.7])
para("Count every visible suture on the short half and write the number in sutures_visible.")

doc.add_heading("Dorsal face (both halves, whole structure)", level=2)
picture(FIG / f"protocol_Bottom_{FIG_SPECIMEN}.jpg", caption="Dorsal face. B14 (purple) is the bottom of the gap "
        "between the tips, computed by the software from the fork trace.")
para("Anchors: click in this order (13 clicks).", bold=True)
table(["Click", "ID", "Where", "Old #"], anchor_rows("Bottom", BOTTOM_WHERE), [0.5, 0.6, 4.6, 0.8])
para("Curves: trace in this order.", bold=True)
table(["Order", "Name", "Trace", "Points"], [
    (1, "B.fork", "From B01 back along the inner edge of the long tip, round the bottom of the gap between the tips, "
                  "and out along the inner edge of the short tip to B02. Follow the gap you can see background "
                  "through, not the pale slit that sometimes continues further back.", "3 + 3"),
    (2, "B.outL", "From B03 along the long tip's outer edge to B01.", 3),
    (3, "B.outS", "From B07 along the short tip's outer edge to B02.", 3),
    (4, "B.sideL", "From B06 back along the long half's outer edge to the shoulder B12.", 6),
    (5, "B.sideS", "From B10 back along the short half's outer edge to the shoulder B13.", 6),
], [0.6, 0.9, 4.3, 0.7])
para("Nothing is traced or clicked on the lobes behind the shoulders, or on their proximal edges. These can be "
     "hidden by membrane or the basal flap on these samples.")

doc.add_heading("Rules", level=2)
steps([
    "**Sclerite, not membrane.** Trace the edge of the amber/dark cuticle. The pale, translucent fringe around the "
    "heel and over the basal lobes is not part of the lance.",
    "**Not attached structures.** Thin golden rods and the golden basal flap that touch the lance are not part of it: "
    "do not trace onto them; cut across at the point where they join the lance's edge.",
    "**Count sutures the same way every time**: from the heel on the Right and Left faces, from the apex on the "
    "Dorsal face.",
    "**Flag, don't guess.** If a point is hidden or damaged, click your best estimate to keep the numbering and write "
    "its ID in flagged_points.",
    "**Points in order.** The software checks that sutures run in order along the edge and warns if two were clicked "
    "in the wrong order.",
])

doc.add_heading("Annotation sheet (one row per image)", level=2)
table(["Column", "What to write"], [
    ("sample_id", "Specimen ID, as in the file name."),
    ("view", "R, L or B."),
    ("image_file", "The raw TIFF's file name."),
    ("roi_file", "The ROI set you saved (SampleID_R_ROI.zip etc.)."),
    ("px_per_mm", "“Distance in pixels” from Set Scale on the 1 mm scale bar."),
    ("digitizer", "Your initials."),
    ("date", "Date digitized."),
    ("flagged_points", "IDs of anchors you couldn't see properly, separated by spaces (e.g. B12 B13); blank if none."),
    ("sutures_visible", "Right/Left: number of sutures you can see on that half. Dorsal: leave blank."),
    ("notes", "Anything unusual (damage, debris, focus)."),
], [1.5, 5.0])

doc.add_heading("After digitizing: converting ROI sets to landmarks", level=2)
steps([
    "From the repository root, run: python novel_genai_landmarking_protocol/tools/roi_to_landmarks.py auto "
    "--table all_landmarks.csv path/to/*_ROI.zip",
    "Each ROI set gets a SampleID_V_ROI_landmarks.csv (Right 42 points, Left 40, Dorsal 38), and all_landmarks.csv "
    "gets one row per image.",
    ("Read the messages:", [
        "OK: converted with no issues.",
        "WARN: converted, but check the named item (e.g. a trace end far from its anchor, a curve with an unexpected "
        "name, or sutures out of order).",
        "FAIL: not converted. Usually the wrong number of anchors or curves; fix the ROI set and rerun."]),
])

# ------------------------------------------------------------------ appendix
doc.add_page_break()
doc.add_heading("Appendix: old (v2) point numbers and the new points", level=1)
para("Anchors with an old number re-use the old point's definition (R02/R03 and L02/L03 are redefined slightly: a "
     "tissue junction and a deepest notch instead of “lowest”/“most recessed”). Old points not listed are retired: "
     "constructions (“equidistant”, “directly above”) became software-placed semilandmarks, and the tongue-and-groove "
     "× heel point (old R29/L25) was dropped as inconsistent.", size=11)
for view, label in (("Right", "Right face"), ("Left", "Left face"), ("Bottom", "Dorsal face")):
    rows = []
    for p in VIEWS[view]["points"]:
        if p["role"] == "semilandmark":
            continue
        old = p.get("old_protocol_point")
        rows.append((p["id"], "anchor" if p["role"] == "anchor" else "computed", p["definition"],
                     old if old else ("replaces 9" if p["id"] == "B14" else "new")))
    para(f"{label}: retired old points {', '.join(map(str, VIEWS[view]['old_points_retired']))}", bold=True, size=11)
    table(["ID", "Role", "Definition", "Old #"], rows, [0.6, 0.9, 4.2, 0.8])

# python-docx's default template has <w:zoom> without the required w:percent
for z in doc.settings.element.iter(qn("w:zoom")):
    if z.get(qn("w:percent")) is None:
        z.set(qn("w:percent"), "100")
doc.save(OUT)
print(f"wrote {OUT}")
