"""Generates lance_landmarking/Lance_Landmarking_CNN_Methods.docx.

Rerun this after any methods/results change (loss function, hyperparameters,
new eval numbers, etc.) rather than hand-editing the .docx -- the .docx is a
build artifact of this script, not the source of truth.

Usage (from repo root, with the project venv active):
    python3 lance_landmarking/tools/docgen/make_methods_docx.py

Needs: python-docx (pip install python-docx; not in requirements.txt since
it's a docs-authoring dependency, not part of the training pipeline).
"""
import re
import subprocess
from datetime import date
from pathlib import Path

from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

REPO_ROOT = Path(__file__).resolve().parents[3]
OUT = REPO_ROOT / "lance_landmarking" / "cnn" / "Lance_Landmarking_CNN_Methods.docx"

# ---------------------------------------------------------------- living facts
# Things that change as the analysis progresses. Update THESE, not prose,
# when a run finishes -- everything below regenerates from them.
try:
    GIT_COMMIT = subprocess.check_output(
        ["git", "rev-parse", "--short", "HEAD"], cwd=REPO_ROOT, text=True
    ).strip()
except Exception:
    GIT_COMMIT = "unknown"
DOC_DATE = date.today().isoformat()
STATUS_NOTE = (
    "Status: living draft. All three views have now been trained and evaluated on the full dataset (Section 7)."
)

NAVY = RGBColor(0x1F, 0x3A, 0x5F)
GREY = RGBColor(0x55, 0x55, 0x55)

doc = Document()
sec = doc.sections[0]
sec.page_width, sec.page_height = Inches(8.5), Inches(11)
for side in ("left_margin", "right_margin", "top_margin", "bottom_margin"):
    setattr(sec, side, Inches(1))


def set_font(style, name, size, bold=None, color=None):
    style.font.name = name
    style.element.rPr.rFonts.set(qn("w:eastAsia"), name)
    style.font.size = Pt(size)
    if bold is not None:
        style.font.bold = bold
    if color is not None:
        style.font.color.rgb = color


set_font(doc.styles["Normal"], "Calibri", 10.5)
doc.styles["Normal"].paragraph_format.space_after = Pt(6)
doc.styles["Normal"].paragraph_format.line_spacing = 1.1
set_font(doc.styles["Heading 1"], "Calibri", 15, True, NAVY)
doc.styles["Heading 1"].paragraph_format.space_before = Pt(16)
doc.styles["Heading 1"].paragraph_format.space_after = Pt(6)
set_font(doc.styles["Heading 2"], "Calibri", 12, True, NAVY)
doc.styles["Heading 2"].paragraph_format.space_before = Pt(10)
doc.styles["Heading 2"].paragraph_format.space_after = Pt(4)
for name in ("List Bullet", "List Number"):
    set_font(doc.styles[name], "Calibri", 10.5)
    doc.styles[name].paragraph_format.space_after = Pt(3)

TOKEN = re.compile(r"(\*\*.+?\*\*|`.+?`)")


def add_runs(p, text, size=None, color=None, italic=False):
    for part in TOKEN.split(text):
        if not part:
            continue
        if part.startswith("**"):
            r = p.add_run(part[2:-2])
            r.bold = True
        elif part.startswith("`"):
            r = p.add_run(part[1:-1])
            r.font.name = "Consolas"
            r._element.rPr.rFonts.set(qn("w:eastAsia"), "Consolas")
            r.font.size = Pt((size or 10.5) - 1)
        else:
            r = p.add_run(part)
        if size and not part.startswith("`"):
            r.font.size = Pt(size)
        if color is not None:
            r.font.color.rgb = color
        if italic:
            r.italic = True
    return p


def H1(t):
    doc.add_heading(t, level=1)


def H2(t):
    doc.add_heading(t, level=2)


def P(t, **kw):
    return add_runs(doc.add_paragraph(), t, **kw)


def B(t):
    return add_runs(doc.add_paragraph(style="List Bullet"), t)


def N(t):
    return add_runs(doc.add_paragraph(style="List Number"), t)


def CAP(t):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(8)
    p.paragraph_format.space_after = Pt(3)
    p.paragraph_format.keep_with_next = True
    add_runs(p, t, size=9.5, color=GREY, italic=True)


def shade(cell, fill):
    tcPr = cell._element.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), fill)
    tcPr.append(shd)


def TABLE(headers, rows, widths, size=9):
    assert abs(sum(widths) - 6.5) < 0.01, sum(widths)
    t = doc.add_table(rows=1, cols=len(headers))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False

    def fill(cell, text, bold=False):
        cell.text = ""
        p = cell.paragraphs[0]
        p.paragraph_format.space_after = Pt(1)
        p.paragraph_format.line_spacing = 1.0
        add_runs(p, ("**%s**" % text) if bold else text, size=size)

    for i, h in enumerate(headers):
        fill(t.rows[0].cells[i], h, bold=True)
        shade(t.rows[0].cells[i], "D9E2F3")
    trPr = t.rows[0]._tr.get_or_add_trPr()
    hd = OxmlElement("w:tblHeader")
    hd.set(qn("w:val"), "true")
    trPr.append(hd)
    for r in rows:
        cells = t.add_row().cells
        for i, v in enumerate(r):
            fill(cells[i], v)
    for row in t.rows:
        cant = OxmlElement("w:cantSplit")
        row._tr.get_or_add_trPr().append(cant)
        for i, c in enumerate(row.cells):
            c.width = Inches(widths[i])
    doc.add_paragraph().paragraph_format.space_after = Pt(2)
    return t


# footer page number
fp = sec.footer.paragraphs[0]
fp.alignment = WD_ALIGN_PARAGRAPH.CENTER


def field(par, instr):
    r = par.add_run()
    for kind, txt in (("begin", None), (None, instr), ("end", None)):
        if kind:
            e = OxmlElement("w:fldChar")
            e.set(qn("w:fldCharType"), kind)
        else:
            e = OxmlElement("w:instrText")
            e.set(qn("xml:space"), "preserve")
            e.text = txt
        r._r.append(e)
    r.font.size = Pt(9)
    r.font.color.rgb = GREY


rr = fp.add_run("Automated lance landmarking: methodology  |  page ")
rr.font.size = Pt(9)
rr.font.color.rgb = GREY
field(fp, "PAGE")

# ------------------------------------------------------------------ title
t = doc.add_paragraph()
t.paragraph_format.space_after = Pt(2)
r = t.add_run("Automated Landmarking of the Neodiprion Ovipositor Lance")
r.bold = True
r.font.size = Pt(22)
r.font.color.rgb = NAVY
t = doc.add_paragraph()
t.paragraph_format.space_after = Pt(4)
r = t.add_run("Methodology, tools, and rationale")
r.font.size = Pt(14)
r.font.color.rgb = GREY
P(
    f"Project: g0-splits-project  |  Code state: git commit `{GIT_COMMIT}`  |  Document date: {DOC_DATE}  |  "
    + STATUS_NOTE,
    size=9.5,
    color=GREY,
)

# ------------------------------------------------------------------ 1
H1("1. Purpose and scope")
P(
    "Manually placing landmarks on the second valvula (\"lance\") of Neodiprion sawflies in ImageJ is accurate but slow. "
    "This project trains a convolutional neural network (CNN) on lances that were already landmarked by hand, so that new "
    "specimens can be landmarked automatically and passed to the existing geometric-morphometric (geomorph) workflow."
)
P(
    "This document records the data, methods, software (with version numbers) and computing environment, and gives the reason "
    "for each design choice, including approaches that were tried and abandoned. Section 7 reports full-dataset test results for all three views. "
    "The decisive validation -- comparing predicted versus manual landmarks through the geomorph/Procrustes pipeline, and against a human-repeatability baseline -- has not yet been run (Section 8)."
)

# ------------------------------------------------------------------ 2
H1("2. Approach at a glance")
N("**Extract ground truth.** Read the landmark coordinates that ImageJ embedded in each previously landmarked TIFF (pixel space, sub-pixel precision).")
N("**Match and quality-control.** Link each raw image to its landmarked TIFF and coordinate file; flag, rather than guess at, any inconsistency; write a single manifest.")
N("**Split by family.** Assign individuals to training, validation and test sets so that siblings never straddle sets.")
N("**Train one CNN per view** (Bottom: 17 landmarks, Left: 32, Right: 36). Each image is resized to 512 x 512; an ImageNet-pretrained ResNet-18 encoder and a deconvolution head produce one map per landmark; a soft-argmax coordinate loss (DSNT) trains the network on landmark position directly.")
N("**Evaluate on held-out individuals** in pixels and millimetres, and compare against a naive baseline that any model must beat.")
N("**Run on CPU.** Develop and test locally (WSL2); train the full three-view job on the MCC cluster through SLURM.")

# ------------------------------------------------------------------ 3
H1("3. Data")
H2("3.1 Specimens, imaging and the manual landmarking protocol")
P(
    "Imaging and landmarking follow the lab protocol (Lance_Imaging_Morphometrics_v2). Lances were photographed with a camera on a Nikon "
    "microscope at fixed 5x magnification (4K frame, 3840 x 2160 pixels), from three angles, and landmarked in ImageJ (version 1.53t, as recorded in the TIFF metadata) "
    "with the multipoint tool, in a fixed order. Before digitizing, ImageJ's global scale was set to 927 pixels = 1 mm, so the exported XY files are in millimetres."
)
B("**Three views per lance:** Right (36 landmarks), Left (32) and Bottom/dorsal (17). Landmark number is landmark identity; the order never changes.")
B("**Landmarks** are defined in the protocol as, for example, the heel, the bottom-most points of the sutures, the lance tip and the margins of the cuticular window. A minority are defined as functions of others (\"two equidistant points between X and Y\", \"the point directly above landmark N\").")
B("**Cross types:** pure-species parents (folders Parents and Non_Laying_Parents), F1 hybrids, and backcross individuals (LBX and PBX).")
B("**Two imaging sessions.** The Parents images are 2560 x 1920 pixels at 1260 pixels/mm; all others are 3840 x 2160 at 927 pixels/mm.")

H2("3.2 Ground-truth coordinates")
P(
    "Each landmarked TIFF carries the original ImageJ multipoint ROI in its IJMetadata tag (TIFF tag 50839), in pixel space at sub-pixel precision. "
    "The pipeline decodes this ROI and uses it as ground truth. The mm-valued text files serve only as a cross-check. "
    "Converting the text files (pixels = mm x resolution) reproduced the ROI coordinates to sub-pixel agreement on the samples checked."
)
P(
    "**Why the ROI and not the text files:** training is done in image pixel space, and the millimetre files would need a per-image calibration that differs between the two imaging sessions (927 versus 1260 pixels/mm) and does not exist on unmarked images. "
    "**Why raw images as network input:** the landmarked TIFFs have the landmark dots drawn into the pixels, so they cannot be used as input."
)

H2("3.3 Manifest and quality control")
P(
    "`build_manifest.py` matches raw image, landmarked TIFF and coordinate file for every individual and view. File names contain many inconsistencies (mixed delimiters, letter case, stray characters, duplicate-copy suffixes, differently named subfolders), so the matcher normalizes names and flags anything it cannot resolve, rather than guessing."
)
B("**960** landmarked images were indexed; **942** are usable (Bottom 308, Left 318, Right 316). This is 921 with no flags plus 21 whose only flag is a byte-identical duplicate coordinate export.")
B("**18 images excluded:** 15 with no matching raw image, 2 with the wrong landmark count (18 instead of 17 and 33 instead of 32, both stray extra clicks), and 1 with a coordinate file but no landmarked TIFF (so no calibration source).")
B("**33 files** belonging to individuals filed under the wrong cross-type folder were relocated after detecting them through their imaging calibration and raw-image match.")

H2("3.4 Training, validation and test split")
P(
    "Individuals are split within each cross type, targeting 70 / 15 / 15. Splitting is by **family** (cross and replicate identifier, with individual and version suffixes removed), using a fixed random seed of 42. "
    "Because whole families move together, the realized proportions differ by view (Table 1). The training and evaluation scripts derive the identical split."
)
CAP("Table 1. Images per split for each view.")
TABLE(
    ["View", "Landmarks", "Train", "Validation", "Test"],
    [
        ["Bottom", "17", "198", "54", "56"],
        ["Left", "32", "228", "38", "52"],
        ["Right", "36", "230", "46", "40"],
    ],
    [1.5, 1.3, 1.2, 1.3, 1.2],
)
P(
    "**Rationale:** siblings share appearance and rearing conditions, so an image-level split would leak information and overstate accuracy. Stratifying by cross type gives every split some hybrids, backcrosses and parents, so generalization across cross types can be measured. "
    "The validation set selects the best training epoch; the test set is used only for final reporting. With 40 to 56 test images per view, and 3 to 23 images per cross type, accuracy estimates carry considerable uncertainty."
)

# ------------------------------------------------------------------ 4
H1("4. Model and training")
H2("4.1 Preprocessing")
P(
    "Each raw TIFF is converted to 8-bit RGB (alpha channels dropped), resized to fit inside 512 x 512 pixels with its aspect ratio preserved, and padded with black (\"letterboxing\"). Landmark coordinates receive the identical scale and offset. "
    "Pixels are normalized with ImageNet mean and standard deviation, matching the pretrained encoder. No data augmentation is applied in the current version."
)
P(
    "**Rationale:** letterboxing keeps lance geometry undistorted and lets one fixed input size serve both imaging sessions. The trade-off is resolution: the lance occupies only part of each frame (median extent about 387 x 138 px for Bottom and 1130 to 1190 x 350 px for Left and Right, in a 3840-px-wide frame), so after resizing it is about 52 px wide in Bottom and about 150 to 160 px in Left and Right. A lance-centered crop is the main planned improvement (Section 8)."
)

H2("4.2 Architecture")
P(
    "One model is trained per view, because the views have different landmark counts and different anatomy. Each model is an ImageNet-pretrained ResNet-18 encoder (torchvision) truncated after its final residual stage (stride 32, 512 channels), followed by three transposed-convolution stages (4 x 4 kernels, stride 2, with batch normalization and ReLU; 512 to 256 to 256 to 256 channels) that restore the resolution to stride 4, and a final 1 x 1 convolution that outputs one map per landmark. A 512 x 512 input produces 128 x 128 maps. The network has about 15 million parameters."
)
P(
    "**Rationale:** this is the standard \"simple baselines\" design for landmark and pose estimation. Pretrained encoder layers supply general edge and texture detectors, which matters with only about 200 training images per view. The model is also small enough to train on CPUs (Section 5), because the MCC cluster has no GPUs."
)

H2("4.3 Training objective")
P(
    "**First attempt: Gaussian heatmap regression (mean squared error).** Each landmark was represented as a Gaussian blob (sigma = 2 map pixels) and the network was trained to reproduce it. This failed on the Right view: the loss stalled at 0.000766, which is the loss of predicting an all-zero map (pi x sigma^2 / 128^2 = 0.000767), the predicted peak height was 0.0045 against a target of about 1, and the test error was about 2,069 px (random). "
    "A 16-image overfit test showed that neither Right nor Bottom left this state in 300 steps. Two remedies were tested on a Right subset: up-weighting pixels near landmarks, and a lower learning rate with warm-up. Neither helped (the weighted variants were worse)."
)
P(
    "**Adopted: soft-argmax coordinate regression (DSNT).** A spatial softmax over each map gives a probability distribution; its expected (x, y) position is the predicted landmark. The loss is the Euclidean distance to the true position (scaled by half the map width) plus a Jensen-Shannon divergence term (weight 1.0) between the softmax map and the normalized Gaussian target, which keeps each map single-peaked."
)
P(
    "**Rationale:** the loss is defined on landmark position, so no all-zero solution exists and gradients are informative from the first step. It optimizes the quantity of interest directly, and its output is sub-pixel by construction. "
    "In the same 16-image overfit test, this loss fit all three views within 60 to 100 steps (training-image error 1.3 px Right, 1.5 px Left, 2.1 px Bottom, in 512-px input space, versus 40 to 55 px for a map-centre guess)."
)

H2("4.4 Optimization and checkpointing")
B("**Optimizer:** Adam, initial learning rate 1e-3, cosine decay to 1% of that value over 40 epochs, batch size 8. Rationale: constant-rate validation error was noisy after epoch 8 in the local Right run, so a decay was added.")
B("**Model selection:** the checkpoint with the lowest validation position error is kept as `best.pt`. A full checkpoint (weights, optimizer state, epoch, history) is written every epoch so a run can be resumed after an interruption.")
B("**Speed measure:** decoding the LZW-compressed TIFFs is about two thirds of the cost of each sample and there is no augmentation, so the resized images are cached in memory after the first epoch.")

H2("4.5 Evaluation protocol")
P(
    "On the held-out test images, predicted positions are mapped back through the inverse of the resizing to original image pixels, and error is the Euclidean distance to the manual landmark. Millimetre error uses each image's own calibration (927 or 1260 pixels/mm), read from its TIFF header. Results are reported overall, per landmark and per cross type."
)
P(
    "**Baseline (essential context).** The imaging protocol places the lance in nearly the same position in every frame, so a predictor that ignores the image and outputs the training-set mean landmark position for the image's cross type already scores well. "
    "Every model is therefore compared with this \"mean-position\" baseline. Beating it clearly is what shows that the model has learned individual shape variation, which is the signal a morphometric analysis needs."
)

# ------------------------------------------------------------------ 5
H1("5. Computing environment and software")
CAP("Table 2. Environments. Development was done locally; full training runs on MCC.")
TABLE(
    ["Item", "Local development", "Morgan Compute Cluster (MCC)"],
    [
        ["Operating system", "Ubuntu 26.04.1 LTS on WSL2 (kernel 6.18.33.2-microsoft-standard-WSL2)", "Linux compute nodes (version not recorded)"],
        ["Hardware used", "AMD Ryzen 9 6900HS; 8 cores and 12 GB RAM allocated to WSL; no GPU used", "AMD EPYC 7702P nodes (128 cores, 512 GB); job requests 32 cores and 64 GB; MCC has no GPUs"],
        ["Python", "3.14.4", "3.12.14 (conda environment from the Miniconda3 module)"],
        ["Job scheduler", "n/a", "SLURM (version not recorded); array of 3 tasks, one per view"],
    ],
    [1.3, 2.6, 2.6],
)
CAP("Table 3. Software and versions. Package versions are identical on both systems unless noted.")
TABLE(
    ["Software", "Version", "Role"],
    [
        ["PyTorch (CPU build)", "2.14.0", "Neural-network training and inference"],
        ["torchvision (CPU build)", "0.29.0", "ResNet-18 architecture and ImageNet-pretrained weights"],
        ["NumPy", "2.5.2", "Array computation"],
        ["Pillow", "12.3.0", "Image resizing"],
        ["tifffile", "2026.9.15", "TIFF pixel and metadata reading, including the embedded ImageJ ROI"],
        ["imagecodecs", "2026.8.16", "LZW decompression required by tifffile for the raw TIFFs"],
        ["Matplotlib", "3.11.2", "Loss-curve figures"],
        ["ImageJ", "1.53t", "Original manual landmarking (version taken from TIFF metadata)"],
        ["R / geomorph", "4.6.1 / 4.1.1", "Downstream Procrustes and shape analysis (installed in the local WSL environment)"],
        ["SciPy, python-docx", "1.18.1, 1.2.0", "Local only; SciPy is installed but not used by the pipeline; python-docx generated this document"],
    ],
    [1.9, 1.2, 3.4],
)
H2("5.1 Cluster job configuration")
B("**Layout:** one SLURM array of 3 tasks (Bottom, Left, Right), each 1 node, 1 task, 32 CPUs, 64 GB, partition `normal`. Each task trains, then evaluates on the test split. The wall-time request is a ceiling (14 days); the expected run time is about 25 minutes per view.")
B("**Measured speed:** on MCC a calibration run of Right took 87 s for epoch 1 (which includes decoding the images once) and 32 s for epoch 2, so 40 epochs is about 22 minutes plus evaluation.")
B("**Robustness measures:** the job calls the environment's Python by full path (a loaded module can otherwise put a different Python first on the path); it checks that all packages import before training; and per-epoch checkpoints allow `--resume` after an interruption.")
P("**Why CPU-only PyTorch on this cluster:** MCC provides no GPUs, and the ResNet-18-based model is small enough for CPU training to be practical (about 32 s per epoch on 32 cores).")

# ------------------------------------------------------------------ 6
H1("6. Design decisions and rationale")
CAP("Table 4. Main decisions, alternatives, and reasons.")
TABLE(
    ["Decision", "Alternatives", "Reason"],
    [
        ["Custom CNN per view", "DeepLabCut, SLEAP, ML-morph (not benchmarked here)", "The 17/32/36-point scheme is novel and not in the literature, so full control over outputs, coordinate handling and evaluation was preferred. A head-to-head comparison with off-the-shelf tools has not been run."],
        ["Ground truth from the embedded ROI", "The mm text files", "Pixel-space, sub-pixel, and independent of the session-specific calibration."],
        ["Separate model per view", "One shared network with several output heads", "Different landmark counts and anatomy; simplest correct baseline. A shared encoder is possible later."],
        ["ResNet-18 with a deconvolution head", "Larger backbones, U-Net variants", "Standard pose-estimation design; pretrained features suit small data; trainable on CPU."],
        ["Soft-argmax (DSNT) loss", "Gaussian-heatmap MSE, with or without foreground weighting", "MSE collapsed to blank maps; DSNT has no blank solution and fit all three views in the overfit test."],
        ["All landmarks trained directly", "Predict only independent landmarks and compute the protocol-derived ones geometrically", "The protocol wording (\"equidistant\", \"directly above\") is not precise enough to encode with confidence. The independent/derived split is recorded for future use."],
        ["Family-level split", "Random image-level split", "Prevents sibling leakage, which inflates accuracy."],
        ["Whole-frame 512 x 512 input", "Lance-centered crop; higher input resolution", "Simplicity and no extra detection stage. Limits precision (Section 8)."],
        ["Compare with the mean-position baseline", "Report raw error only", "The lance is protocol-standardized, so raw error alone overstates learning."],
        ["CPU training, 0 loader workers with image cache", "Parallel DataLoader workers", "No GPU on MCC. Decoding once and caching avoids competing with the compute threads."],
    ],
    [1.7, 1.9, 2.9],
    size=8.5,
)

# ------------------------------------------------------------------ 7
H1("7. Results")
P("Error is Euclidean distance on held-out test images, in original image pixels, with millimetre values from each image's calibration. The baseline is the mean-position predictor of Section 4.5. Final numbers below are from the full 40-epoch DSNT run of all three views on MCC (job 36764579, 2026-09-22); earlier partial/failed runs are kept in the table for context.")
CAP("Table 5. Test error by model and view.")
TABLE(
    ["View", "Model / run", "Mean px (mm)", "Median px", "Baseline mean / median px", "Comment"],
    [
        ["Bottom", "Gaussian-MSE heatmap, 100 epochs, MCC", "24.3 (0.024)", "15.6", "37.3 / 26.9", "Learned, but only 1.5 to 1.7 times better than baseline"],
        ["Right", "Gaussian-MSE heatmap, 100 epochs, MCC", "2069 (2.15)", "2155", "39.4 / 30.6", "Collapsed to blank maps"],
        ["Right", "DSNT, 12 epochs, local", "20.0 (0.021)", "16.9", "39.4 / 30.6", "Early check; superseded by the full run below"],
        ["Right", "DSNT, 2-epoch MCC calibration run", "50.5 (0.050)", "31.8", "39.4 / 30.6", "Not converged; used to check the pipeline and timing"],
        ["Bottom", "DSNT, 40 epochs, full data, MCC", "15.9 (0.017)", "10.6", "37.3 / 26.9", "2.35x better than baseline"],
        ["Left", "DSNT, 40 epochs, full data, MCC", "11.8 (0.012)", "9.7", "40.3 / 27.8", "3.40x better than baseline"],
        ["Right", "DSNT, 40 epochs, full data, MCC", "12.6 (0.013)", "10.0", "39.4 / 30.6", "3.13x better than baseline"],
    ],
    [0.7, 1.75, 0.9, 0.65, 1.0, 1.5],
    size=8.5,
)
CAP("Table 6. Test error by cross type, full 40-epoch DSNT models (model mean px / baseline mean px, image-level).")
TABLE(
    ["Cross type", "Bottom (n)", "Left (n)", "Right (n)"],
    [
        ["F1", "11.1 / 86.3 (2)", "9.3 / 109.9 (3)", "10.5 / 91.1 (3)"],
        ["Parents", "13.6 / 81.4 (7)", "16.2 / 72.2 (7)", "13.5 / 54.7 (7)"],
        ["LBX", "19.7 / 40.7 (23)", "11.3 / 38.7 (23)", "13.2 / 34.6 (23)"],
        ["Non_Laying_Parents", "26.9 / 41.5 (4)", "12.5 / 22.6 (5)", "11.9 / 19.2 (4)"],
        ["PBX", "10.6 / 12.3 (20)", "10.9 / 18.2 (14)", "8.6 / 15.1 (3)"],
        ["Images worse than baseline", "8 / 56", "3 / 52", "1 / 40"],
    ],
    [1.7, 1.6, 1.6, 1.6],
)
P(
    "**Reading the results.** All three views now clearly beat the mean-position baseline for almost every cross type; the one near-tie (Bottom/PBX, 1.16x) is a group where the baseline was already accurate, not a case where the model did poorly in absolute terms (10.6 px). "
    "F1's large relative gains (8 to 12x) reflect a poor baseline for that group (few training images), not unusually good absolute F1 accuracy."
)
P(
    "**Visual check (`runs/21ix26_runs/qc/overlay_worst_median_best.png`, not reproduced here): errors are concentrated, not diffuse.** Plotting predicted versus manual landmarks on the worst-, median-, and best-scoring test image per view shows two distinct, recurring failure patterns rather than uniform noise: "
    "(1) the heel-region landmarks (numbers 1 to 3 in Left and Right; the 'split point' landmark 9 in Bottom, a clear outlier at 43.4 px mean versus 18.2 px for the next-worst landmark) are occasionally placed well off the specimen entirely, in blank background -- this recurs across every run, MSE and DSNT alike, and looks like a genuinely hard-to-localize feature rather than a training artifact; "
    "(2) Bottom's worst images additionally show closely-spaced suture landmarks becoming jumbled with each other, consistent with Bottom's low in-frame resolution (the lance is only about 52 px wide after the current preprocessing). "
    "These are two separate problems with two different likely fixes (Section 8), and most predictions -- the median and best cases in every view -- track the cuticle edge tightly."
)

# ------------------------------------------------------------------ 7.1
H2("7.1 Downstream validation: does shape analysis reach the same conclusions? (test set)")
P(
    "The px/mm error in Table 5 says nothing about whether prediction error is large or small relative to real shape "
    "variation among specimens, which is what a geomorph analysis actually depends on. To check this, manual and "
    "predicted landmarks for the test-set individuals (never seen in training) were pooled into a single GPA "
    "superimposition per view -- aligning them separately would let each set rotate independently to its own mean "
    "shape and could offset an individual's manual and predicted landmarks even if the underlying points are nearly "
    "identical, so a shared alignment is what makes a direct per-individual comparison meaningful."
)
CAP("Table 6.1. Manual-vs-predicted shape comparison, test set, shared GPA alignment per view.")
TABLE(
    ["View", "Paired dist. / between-individual dist.", "Group R2: manual -> predicted", "Method effect (R2, p)"],
    [
        ["Bottom", "63.1%", "0.358 -> 0.525", "0.050, p=0.001 (significant)"],
        ["Left", "52.7%", "0.318 -> 0.476", "0.007, p=0.354 (n.s.)"],
        ["Right", "57.3%", "0.197 -> 0.315", "0.009, p=0.457 (n.s.)"],
    ],
    [1.1, 2.2, 1.9, 1.3],
)
P(
    "**Paired distance versus between-individual distance** is each individual's own manual-vs-predicted Procrustes "
    "distance (shared alignment), compared with the average Procrustes distance between different individuals in the "
    "manual data alone. In all three views prediction error is well under half to two-thirds of real between-"
    "individual shape variation -- the main reassurance this check was meant to provide."
)
P(
    "**Group (cross-type) effect** is the R-squared from `procD.lm(coords ~ Group)`, run once on manual landmarks and "
    "once on predicted landmarks. Cross-type separation survives, and its R-squared is higher under predicted "
    "landmarks in every view. **This is not necessarily evidence that predicted landmarks are more accurate than "
    "manual ones** -- a model trained with limited data can smooth out genuine individual variation along with "
    "digitizing noise, which would also inflate apparent group separation by shrinking within-group spread. This "
    "point needs the human-repeatability baseline (Section 8) to resolve."
)
P(
    "**Method effect** is whether landmarking method (manual vs. predicted) itself explains shape variance beyond "
    "Group, from `procD.lm(coords ~ Group + Method)` on the pooled data. It is small and not statistically "
    "significant for Left and Right. **Bottom is the exception:** a small but real systematic shift (R-squared 0.05, "
    "p=0.001), consistent with the heel/suture failure modes in Section 7 -- its PCA plot shows several individuals "
    "with manual-to-predicted shifts spanning nearly the full first principal component, versus short shifts for "
    "Left and Right."
)
P("Code: `lance_landmarking/cnn/export_predictions.py` (export, validated by exactly reproducing Table 5's px error from the exported CSVs) and `lance_landmarking/analysis/compare_manual_vs_predicted.R` (GPA/procD.lm/PCA); outputs in `lance_landmarking/analysis/output/`.")

# ------------------------------------------------------------------ 8
H1("8. Limitations and planned work")
B("**Small test sets and a single split** (40 to 56 images per view; 3 to 23 per cross type). Cross-validation would give tighter estimates.")
B("**Precision.** Errors sit near the resolution floor of the current input. A lance-centered crop or higher input resolution is the main lever.")
B("**Is it accurate enough? Partly established.** Section 7.1's shape-level comparison is reassuring (prediction error well under real between-individual variation, cross-type separation preserved), but on its own it cannot rule out the regression-toward-the-mean effect noted there, and it does not say what a human observer's own error looks like on the same scale. Two observers using this protocol agree at R > 0.90 (as reported for this protocol), but a correlation cannot be compared directly with a landmark distance in millimetres. The remaining decisive check, not yet run: the distance between two human observers' landmarks on the same images, in the same px/mm units as Section 7 -- needed to know whether the model's 10 to 16 px median error is within human noise or exceeds it.")
B("**Two recurring, localized failure modes** rather than uniformly distributed error (Section 7): heel-region landmarks placed off-specimen in all three views, and jumbled suture landmarks specifically in Bottom's worst cases. Section 7.1's shape analysis corroborates this independently -- Bottom is the only view where landmarking method has a statistically detectable effect on shape. These likely need different fixes and have not yet been addressed.")
B("**No data augmentation** yet, and training is not bit-for-bit reproducible because the network's random seed is not fixed (the data split is fixed).")
B("**Derived landmarks** are predicted directly rather than reconstructed from the protocol's geometric definitions.")
B("**Data gaps:** 15 landmarked images have no raw counterpart, and the origin of the earlier unexplained slow epochs on MCC (about 2 hours per epoch with an older configuration) was never isolated.")

# ------------------------------------------------------------------ A
H1("Appendix A. Reproducibility")
P(f"Repository: github.com/RDRidenbaugh/g0-splits-project. Code state at the time of writing: commit `{GIT_COMMIT}`. The raw image data is not stored in the repository.")
CAP("Table 7. Key files (under lance_landmarking/).")
TABLE(
    ["File", "Role"],
    [
        ["tools/landmarks_io.py", "Decodes the embedded ImageJ ROI and TIFF calibration"],
        ["tools/build_manifest.py", "Matches images, extracts ground truth, flags problems; writes manifest.csv"],
        ["cnn/splits.py, dataset.py, heatmap.py", "Family-level split; image loading and resizing; soft-argmax decoding"],
        ["cnn/model.py, train.py, evaluate.py", "Network; training loop with the DSNT loss; test evaluation"],
        ["cnn/train_lance_landmarks.slurm, setup_env.sh, requirements.txt", "MCC job, one-time environment build, pinned versions"],
        ["cnn/export_predictions.py", "Exports manual + predicted test-set landmarks to CSV for the geomorph comparison (Section 7.1)"],
        ["analysis/compare_manual_vs_predicted.R", "GPA/Procrustes/procD.lm/PCA comparison of manual vs. predicted shape (Section 7.1)"],
        ["tools/docgen/make_methods_docx.py", "Generates this document -- rerun after methods/results change"],
    ],
    [2.9, 3.6],
)
P("Typical commands, from lance_landmarking/cnn/ (the manifest builder is run from lance_landmarking/tools/):")
for c in [
    "python3 build_manifest.py",
    "python3 train.py --angle Right --loss dsnt --lr-decay cosine --epochs 40 --batch-size 8 --num-workers 0 --cache-images",
    "python3 evaluate.py --angle Right --checkpoint runs/<run>/best.pt --loss dsnt",
    "sbatch train_lance_landmarks.slurm",
]:
    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Inches(0.3)
    p.paragraph_format.space_after = Pt(2)
    r = p.add_run(c)
    r.font.name = "Consolas"
    r._element.rPr.rFonts.set(qn("w:eastAsia"), "Consolas")
    r.font.size = Pt(9)

# python-docx's default settings.xml template omits a required attribute
for z in doc.settings.element.iter(qn("w:zoom")):
    if z.get(qn("w:percent")) is None:
        z.set(qn("w:percent"), "100")

doc.core_properties.title = "Automated Landmarking of the Neodiprion Ovipositor Lance: Methodology, Tools, and Rationale"
doc.core_properties.subject = "g0-splits-project"
doc.save(OUT)
print("saved", OUT)
