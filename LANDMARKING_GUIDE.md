# Landmarking saws and lances with the CNN models

This guide takes you from new photographs to finished landmark tables, review images and phenotype tables. It covers the saw (protocol v1.2, 52 points) and the lance (protocol v1.4: Right 42, Left 40, Bottom 38 points). You don't need to train anything: the trained models are already in each pipeline's `production/runs/` folder. The last part explains the QC flags and overlays and what to do about each one.

The technical detail behind each step is in `genai_saw_landmarking/production/README.md` and `genai_lance_landmarking/production/README.md`. The landmark definitions are in `genai_saw_landmarking/Saw_Landmarking_Protocol.md` and `genai_lance_landmarking/Lance_Landmarking_Protocol.md`.

---

## Contents

0. [How it works](#0-how-it-works)
1. [One-time setup](#1-one-time-setup)
2. [Before you start: image requirements](#2-before-you-start-image-requirements)
3. [Saws, step by step](#3-saws-step-by-step)
4. [Lances, step by step](#4-lances-step-by-step)
5. [Reviewing the results: QC flags and overlays](#5-reviewing-the-results-qc-flags-and-overlays)
6. [Correcting points in Fiji](#6-correcting-points-in-fiji)
7. [Output files](#7-output-files)
8. [Troubleshooting](#8-troubleshooting)

---

## 0. How it works

```
raw photos ──► calibrate (own scale bar) ──► CNN predicts every point ──► QC flags + overlays
                                                                              │
                                                  you review flagged images ◄─┘
                                                    │ keep / drop  → qc_review.csv
                                                    │ fix points   → Fiji → fiji_corrections.csv
                                                    ▼
                               export_geomorph.py ──► XY tables in mm (+ sliders, key, report)
                                                    ▼
                               *_morphometrics.R ──► GPA/PCA, centroid size, linear measures (phenotype table)
```

**The models.** Each structure has five models (the lance has five per view, so 15), trained with **cross-fitting**. The labelled images were split into five folds by family or colony, and each model was trained on four folds and tested on the fifth. The script picks the model for each image:

| `source` | Used for | Meaning |
|---|---|---|
| `oof_f<k>` | images whose label was used in training | predicted by model *k*, the one model that never saw the image ("out-of-fold") |
| `ensemble` | **every new image**, and old images with no usable label | the mean of all five models |
| `in_sample` | should never happen | a trained image whose held-out model file is missing, so every available model saw it (flagged) |
| `…+fiji` | any of the above | points you corrected by hand in Fiji |

No image is predicted by a model that trained on it, so new images and the original mapping population are measured the same way. **New images always come out as `ensemble`.**

**Expected accuracy** (held-out error per point against the training labels):

| Structure | Mean | Median | Weakest points |
|---|---|---|---|
| Saw | ~6 µm | ~4.7 µm | crowded distal points R6–R7, D6–D7, V5–V7 |
| Lance Right | 11.3 µm | 10.4 µm | heel R02/R03 |
| Lance Left | 11.7 µm | 10.5 µm | heel L02/L03 |
| Lance Bottom | 15.7 µm | 13.5 µm | shoulders B12/B13 |

For comparison, two human digitizers differ by a median of about 2 µm on saws. The CNN is 5.0–5.4 µm from each of them.

---

## 1. One-time setup

**Python (local).** Python 3.12 or newer. From the repository root:

```bash
python3 -m venv .venv
.venv/bin/pip install -r cnn/requirements.txt
```

Run every command below with `.venv/bin/python` (or activate it with `source .venv/bin/activate`). The system `python3` has no numpy. `imagecodecs` must be installed, or the LZW-compressed lance TIFFs won't open.

**Python on MCC** (optional, for large lance batches). Run `cnn/setup_env.sh` once. It builds `.condaenv` at the repository root on scratch.

**Models.** The weights are not in git, so check they are on disk:

```
genai_saw_landmarking/production/runs/v12/saw_f0 … saw_f4/            best.pt, split_keys.json
genai_lance_landmarking/production/runs/v14/{right,left,bottom}_f0 … _f4/   best.pt, split_keys.json
```

If a model is missing, the script prints a warning and uses the models it has. Out-of-fold images whose model is missing are flagged `in_sample`.

**R** (for the morphometrics step): `geomorph`, `dplyr`, `ggplot2`, `readxl`.

**Fiji** (optional, for correcting points): any recent Fiji/ImageJ.

---

## 2. Before you start: image requirements

The models learned from the lab's standard imaging. New images should match it.

| | Saw | Lance |
|---|---|---|
| Format | `.tif` (or `.jpg`), RGB | `.tif`, RGB |
| Size | 2560×1920 (Zeiss) | 3840×2160 or 2560×1920 (Nikon NIS) |
| Scale bar | **burned-in red scale bar, a round length** (e.g. 200 µm, 1 mm) | the same |
| File name | `<ID>_<L or R>.tif`, optional `_v2` (e.g. `NL24KY_X166_AF1_R.tif`) | `<ID>_<R, L or B><frame#>.tif` (e.g. `PBX002V01_B.tif`, `LL280xLL284-1_R2.tif`) |
| Orientation | as imaged. The script puts the apex left and the teeth up | as imaged (standard lance protocol views) |
| Background | any of the session colours (green, pink, grey, white); normalized automatically | the standard background |

**Every image is calibrated from its own scale bar** (lab decision, 2026-09-27). An image without a readable bar gets a fallback value and a flag (see §5). Don't crop the bar out, and don't paint over it with red ID text of the same length.

**The file name matters.**
- Saws: `_L`/`_R` gives the side. For new images (no marked TIFF), the side also gives the orientation: `_R` images are mirrored so the apex points left. A wrong side letter gives a mirrored saw, and the CNN will fail on it (usually flagged `order` or `shape`).
- Lances: the letter after the last `_` gives the view (R, L or B). A file without it is skipped and listed in `unparsed_images.txt`.
- **Keep IDs identical to the PRIME tables and sample sheets.** Metadata and species are joined by ID.

---

## 3. Saws, step by step

All commands run from `genai_saw_landmarking/`. The saw pipeline always processes the **whole** saw image collection: new images are added to the existing ones, and the old ones get identical predictions again.

### Step S1. Put the images in place

```
genai_saw_landmarking/<cohort>/raw_images/<session>/[TIF/]<ID>_<L|R>.tif
```

- `<cohort>` is `g0` or `splits` (or a new cohort folder).
- `<session>` is the imaging date folder (e.g. `27ii26`). It is recorded as `session`, and it is used for the fallback calibration.
- Leave `.czi` files alongside if you have them; they are ignored.

### Step S2. Calibrate from the scale bars

```bash
../.venv/bin/python tools/calibration_survey.py
```

This reads the red bar in every saw image (and the g0 lances) and writes `analysis/data/calibration.csv`.

**Check:** the script prints `N/M calibrated from their own bar`. Open `analysis/data/calibration_problems.csv`, which lists every image whose bar could not be read:
- `cal_source = session_median`: the image has no usable bar and borrows the median of its session. That is usable for now, but re-export the image with a bar if you can.
- `cal_source = none`: no bar and no other image in the session to borrow from. **Fix it before step S5**, or the export has no mm scale for that image.

### Step S3. Prepare the images for the CNN

```bash
cd production
../../.venv/bin/python prep_images.py
```

This writes `production/images/<key>.tif` (orientation set to apex left, teeth up; colour-normalized) and `production/image_table.csv`. `key` is the lower-case file stem, for example `nl24ky_x166_af1_r`. Existing prepared images are not rewritten (use `--overwrite` to force that).

**Check the printed lines:**
- `marked orientation disagrees with filename side: [...]` lists images whose file-name side contradicts their digitized TIFF. Rename those files; the side is probably wrong.
- `duplicate stems renamed: [...]` lists the same file name in two sessions. They become `<key>_2`, `<key>_3`.

### Step S4. Run the CNN

```bash
../../.venv/bin/python landmark_images.py          # ~10 min on CPU for ~400 images
```

The options are `--overlays flagged|all|none` (default `flagged`) and `--workers N`.

This writes:
- `output/predictions_px_saw.csv`: one row per image, with points in pixels of the prepared image, the QC columns, and `flags`.
- `output/overlays/<key>.jpg`: a picture of every flagged image. Use `--overlays all` to draw every image, which is a good idea for a new batch.

The last two printed lines summarize the run, for example:
```
420 images, 5 models: {'oof': 380, 'ensemble': 40}; flagged 27 {'label_gap': 17, 'shape': 8, ...}
label_gap limit 9.8 um (2x the median out-of-fold gap)
```

### Step S5. Review the flagged images

See **§5** for what each flag means. Record every decision in `production/qc_review.csv`:

```csv
key,flags,label_gap_um,source,overlay,decision,note
<new_key>_r,shape,,ensemble,output/overlays/<new_key>_r.jpg,keep,points correct; just a large saw
rb029_f1_r,label_gap,45.8,oof_f4,output/overlays/rb029_f1_r.jpg,drop,annulus shift
```

Only `key` and `decision` (`keep` or `drop`) are read; the other columns are for your notes. Append new rows and keep the existing ones.

To fix points instead of dropping the image, see **§6**.

### Step S6. Metadata for new females

Species, host, treatment, colony and population come from the PRIME tables (`analysis/data/prime_g0_v6.csv`, `prime_splits_v8.csv`, exported from `data/PRIME_Compiled_*.xlsx`). For a female that is **not in PRIME**, or to correct one, add a row to `production/metadata_overrides.csv`:

```csv
ID,species,host,treatment,colony,population,note
<ID>,PINETUM,white,B,<colony>,<population>,not in PRIME; entered by hand <date>
```

Every non-empty cell replaces the computed value for all saws of that female. **Don't edit `Saw_v12_XY.csv` by hand**, because the next export overwrites it.

### Step S7. Export the landmark files

```bash
../../.venv/bin/python export_geomorph.py
```

This writes `output/geomorph/`: `Saw_v12_XY.csv`, `Saw_v12_sliders.csv`, `landmark_key_v12.csv` and `export_report.txt`. See §7.

**Check `export_report.txt`:**
- `N images -> M saws (P pass QC, F flagged)`.
- `saws without PRIME metadata`: add these to `metadata_overrides.csv` (step S6) and export again.
- `fiji_corrections.csv applied to …` and `still dropped by qc_review.csv`: a corrected image that you had also marked `drop`. Set it to `keep`.
- `several images of one saw`: which image was kept when a saw was imaged twice. The order of preference is: passes QC, then out-of-fold, then the smallest model disagreement.

To compare with the previous export without overwriting it, use `--out-dir output/geomorph_test`.

### Step S8. Morphometrics and phenotype table

```bash
SAW_XY_DIR=$PWD/output/geomorph PRIME_DIR=$PWD/../data Rscript saw_v12_morphometrics.R
```

You can also run it in RStudio; the default paths point to the WSL folders. It writes `PRIME_Saw_Pheno_v12.csv`: one row per female, with centroid size, shape PCs and linear measures. `qc_pass` is the single exclusion switch: saws with `FALSE` keep their size and linear measures but get NA shape PCs and are left out of the analyses. For extra outliers found in the PCA, add a `drop` row to `qc_review.csv` and export again, or list the ID in `exclude_ids` in the script.

---

## 4. Lances, step by step

All commands run from `genai_lance_landmarking/production/`. Unlike the saw pipeline, the lance pipeline landmarks **whatever folders you give it**, so a new batch can be run on its own.

### Step L1. Put the images in place

Anywhere works. By convention, a new batch goes in its own folder, for example `genai_lance_landmarking/raw_images/<batch>/`. The mapping population is in `raw_images/{lbx,pbx,f1,parents,non_laying_parents}/`; the folder name becomes the `group` (cross type) unless you pass `--group`.

### Step L2. Run the CNN

**Locally:**
```bash
../../.venv/bin/python landmark_images.py /path/to/new_batch --group PBX --out-dir output_new_batch --overlays all
```

- `paths`: one or more folders or files (default: all of `raw_images/`).
- `--group`: the cross type for these images (`LBX`, `PBX`, `F1`, `Parents`, `G0`…); it sets the species when the ID isn't in `sample_sheet.csv`.
- `--out-dir`: keep each batch separate. The default `output/` holds the mapping population.
- `--views Right,Left`: run only some views.
- `--px-per-mm N`: force one calibration for all images. Use it only when you know the bar is wrong.

**On MCC** (large batches):
```bash
sbatch --export=ALL,IMAGES=/scratch/.../new_batch,GROUP=PBX,OUT=/scratch/.../new_batch_out landmark_v14.slurm
```
This runs both the prediction and the export. Copy `OUT` back when it finishes.

This writes, per view:
- `<out>/predictions_px_<View>.csv`: points in raw-image pixels, calibration and QC columns.
- `<out>/overlays/<View>/<key>.jpg`: an overlay of each flagged image (or of all of them with `--overlays all`).
- `<out>/unparsed_images.txt`: files with no view letter in the name. Rename them and run again.

The printed summary gives, per view, the number of images, how many were out-of-fold, and how many were flagged.

> **Small batches:** the `shape` and `spread` flags compare each image with the *other images in the same run* (see §5). For a batch of fewer than ~50 images, add the mapping population to the run so the reference is stable:
> `landmark_images.py ../raw_images /path/to/new_batch --out-dir output_combined`
> The old images get the same predictions as before.

### Step L3. Review the flagged images

See **§5**. Record decisions in `genai_lance_landmarking/production/qc_review.csv`. This file needs a `view` column, because one key can appear in several views:

```csv
view,key,decision,note
Bottom,<key>_b,drop,lance folded; shoulders not visible
Right,<key>_r,keep,shape flag: large individual; points correct
```

To fix points instead, see **§6**.

### Step L4. Species for new IDs

Species come from `sample_sheet.csv` (`ID,species`). If the ID isn't there, the group (`LBX`, `PBX`, `F1`) is used; for parents the ID prefix is used (`LL`/`LX` = Lecontei, `NP`/`PX` = Pinetum). Add any other new individuals to `sample_sheet.csv`. The export report lists IDs with no species.

### Step L5. Export the landmark files

```bash
../../.venv/bin/python export_geomorph.py --pred-dir output_new_batch
```

This writes `output_new_batch/geomorph/`: `Lance<View>_v14_XY.csv`, `Lance<View>_v14_sliders.csv`, `landmark_key_v14.csv` and `export_report.txt`. Check the report for missing species and for images dropped as duplicates. When an individual has several images of one view, the one kept is the image that passes QC, then the one with the smallest model disagreement.

### Step L6. Morphometrics and phenotype table

```bash
LANCE_XY_DIR=$PWD/output_new_batch/geomorph Rscript lance_v14_morphometrics.R
```

This writes `PRIME_Lance<View>_Pheno_v14.csv`: ID, species, session, centroid size, `Comp1`–`Comp20` and the linear measures (protocol §6.2). It joins to the QTL tables by `ID`. Images with `qc_pass = FALSE` are left out unless `use_flagged <- TRUE`.

> The PCs come from a GPA of the images in *this* table. To put a new batch on the same axes as the mapping population, export the two together (one `--pred-dir` holding both runs, or one combined run as in step L2).

---

## 5. Reviewing the results: QC flags and overlays

### 5.1 What a flag is (and is not)

A flag is a **reason to look**, not a verdict. Flagged images are still written to the predictions table. `export_geomorph.py` sets `qc_pass = FALSE` for them unless you override it. The final `qc_pass` is decided in this order:

1. A `qc_review.csv` decision always wins: `keep` → TRUE, `drop` → FALSE.
2. Otherwise, an image corrected in Fiji → TRUE (the correction clears its flags).
3. Otherwise, no flag → TRUE; any flag → FALSE.
   - Saw exception: `no_scale` alone does not fail an image that borrowed its session's median calibration.

Most flags on a large run are false alarms: about 5% of good images are flagged by design. Look at every overlay. It takes a few seconds each.

### 5.2 Reading an overlay

Overlays are cropped to the specimen and scaled to 1400 px.

| Mark | Meaning |
|---|---|
| **Red circle + ID** | anchor (fixed landmark), e.g. `S01`, `V3`, `R04`, `B12` |
| **Blue circle + ID** | computed point (lance `R18`/`L18` dorsal curve start, `B14` fork crotch) |
| **Yellow small circle** | sliding semilandmark on a curve |
| **Cyan circle + white line** | the image's own training label (only on `oof` images that had a label). The white line joins each labelled point to the CNN's point: long lines = disagreement |
| **Header text** | `key  source  flags` and, when there is a label, `label gap N um` |

The saw overlay is drawn on the **prepared** image: apex left, teeth up, colour-normalized (grey background). The lance overlay is drawn on the raw image.

**For every overlay, check:**
1. **Right specimen, right way up:** apex where it should be; saw teeth up; the lance view matches the file name.
2. **Anchors on their structures, in sequence:**
   - Saw: `V1`→`V7` and `R1`→`R7` step distally along the saw, one per annulus, and `D1`–`D7` sit on the same annuli as the V/R above them. The most common saw failure is an **annulus shift**, where a whole run of points sits one annulus off.
   - Lance: the sutures `R04`→`R10` (ventral ends) and `R12`→`R16` (dorsal ends) run in order from the heel to the apex, each on a real suture; the window ends `R11`/`R17` bracket the window.
   - Bottom: `B01`/`B02` on the two tips, `B03`–`B06` and `B07`–`B10` on the outer suture ends of each half, `B11` in the basal notch, `B12`/`B13` at the shoulders.
3. **Semilandmarks follow the edge:** yellow points on the outline, evenly spaced, not cutting across the specimen or wandering onto debris.
4. **With cyan labels:** decide *who* is wrong. The label is an automatic trace and can be the wrong one; the overlay shows both.

### 5.3 The flags

| Flag | Pipeline | What triggered it | What it usually means | What to do |
|---|---|---|---|---|
| **`label_gap`** | both, `oof` images only | The CNN is far from the image's own training label. Mean point distance: saw > 2× the median gap over all out-of-fold images (~10 µm); lance > 21 µm (Right, Left) or > 27 µm (Bottom), about 2× the typical error | Either the **label** was wrong (the model learned from it anyway, and the held-out CNN disagrees) or the **CNN** failed on a hard image. Saw examples: annulus-identity shifts (`rb029_f1_r`, 46 µm) and debris (`rb017_g0_f7_r`) | Compare the cyan and red points. If the CNN is right, **keep** it. If the CNN is wrong, fix it in Fiji or **drop** it. Note these images: if the models are retrained, their labels should be removed from the manifest. **Never on new images** (they have no label) |
| **`spread`** | saw: `ensemble` only; lance: all images | The five models disagree: mean distance of the models' points from their mean > 3× the run's median | The image is unlike the training images: odd lighting, damage, debris, a new imaging setup, a mis-oriented specimen. **This is the main warning sign for new images** | Look closely. The mean of five disagreeing models is often a plausible-looking compromise between two different answers, so check the anchors against the anatomy. Fix in Fiji or drop. On lance `oof` images, spread is always low (four of the five models trained on the image), so it says little there |
| **`order`** | both | Anchors are out of sequence along the axis. Saw: `V1`…`V7` or `R1`…`R7` not running from proximal to distal (apex → V1 axis); lance: sutures/window ends (`R04`–`R10`, `R11`–`R17`; Bottom `B03`–`B06`, `B07`–`B10`) out of order | Points swapped or collapsed together; a mirrored or upside-down image; a broken specimen | Almost always a real error. Fix in Fiji (drag the points into order; don't renumber) or drop. For a saw, check the file-name side letter |
| **`outside`** | both | A point lies outside the image | The specimen runs off the frame, or the prediction failed badly | Drop, unless the point is only just outside and you can place it in Fiji |
| **`shape`** | both | The Procrustes distance to the run's mean shape is a robust outlier (z > 4) | Either a **real** extreme individual (very large or unusual shape, a hybrid, a different species) or a **bad** prediction that still looks orderly | If every point is on the right structure, **keep** it: dropping real outliers biases the biology. The z-score is relative to the images in the same run, so in a small or one-species batch it flags ordinary variation |
| **`no_scale`** | both | No usable calibration. Saw: no readable bar (the session median was borrowed if one existed); lance: no bar, no NIS tag and an unknown image width | mm values are approximate or missing | Saw with `session_median`: the image passes, but the mm values rely on the session's other images. Otherwise supply a calibration: re-export the image with a bar, or (lance) use `--px-per-mm` |
| **`no_bar`** | lance | No red scale bar found (or only red ID text) | Calibrated from the nominal value: the NIS tag in the TIFF, or 927 px/mm for 3840-wide images | Imagers differ by ~1%, so the mm values may be off by that much. **Keep** it if 1% is acceptable for your question; better, re-export the image with its bar |
| **`scale_bar`** | lance | A red bar was found but is > 2% from every round length (truncated, broken or partly hidden bar, or a zoom change) | Nominal calibration applied | Open the image and check the bar. If the zoom was changed, the nominal value is wrong: set `--px-per-mm` for that image, or drop it |
| **`in_sample`** | both | A training image's held-out model is missing | Every available model saw this image, so the prediction is optimistically accurate | Restore the missing `runs/.../best.pt` and run again. Not normally seen |

### 5.4 Other QC columns in `predictions_px_*.csv`

| Column | Meaning | Rough scale |
|---|---|---|
| `spread_px` | mean distance (px) of the five models' points from their mean | ensemble images, typical: a few px. The flag is at 3× the run's median. Divide by `px_per_mm` and multiply by 1000 for µm |
| `label_gap_um` | mean distance (µm) of the out-of-fold prediction from the image's label | typical ≈ the held-out error in §0 |
| `procrustes_d` | Procrustes distance to the run's mean shape | only meaningful relative to the other rows in the run |
| `px_per_mm`, `cal_source` | the calibration used, and where it came from | saw: `own_bar` / `session_median` / `none`; lance: `scale_bar` / `nis_tiff` / `image_width` / `argument` |
| `scale_bar_um` (lance) | the round length the bar was read as | e.g. 1000 or 200 |

### 5.5 Deciding: keep, fix or drop

```
Is it the right specimen, right way up, fully in frame?        no → drop (or re-image)
Are all anchors on the correct structures, in order?           no → a few points wrong? → fix in Fiji (§6)
                                                                    many / a whole series shifted? → fix or drop
Do the semilandmarks follow the edge?                          no → fix in Fiji, or drop
Is the calibration its own bar?                                no → keep if ~1% is acceptable; note it
                                                              yes → keep
```

- **Keep real outliers.** A `shape` flag on a correctly landmarked specimen is biology.
- **Be consistent.** For saws the lab chose to drop all 25 flagged images of the 2026-09 run (371 of 395 saws pass). Whatever rule you use, write it in the `note` column.
- **Spot-check unflagged images too.** Especially for a new batch, run with `--overlays all` and flip through a sample: a consistent error (for example a new imaging setup) can shift every image without tripping a flag.

---

## 6. Correcting points in Fiji

You can use this for any image, flagged or not. The points keep their identity by their order, so **move points; never add or delete them.**

1. **Write the review TIFFs.**
   - Saw (`genai_saw_landmarking/production/`):
     ```bash
     ../../.venv/bin/python write_roi_tiffs.py                 # every flagged image
     ../../.venv/bin/python write_roi_tiffs.py --keys rb029_f1_r ag078_f3_r
     ../../.venv/bin/python write_roi_tiffs.py --all [--prepared]
     ```
     → `output/roi_tiffs/<key>.tif`, in the protocol frame (apex left, teeth up). `--prepared` shows the colour-normalized CNN input instead of the true colours.
   - Lance (`genai_lance_landmarking/production/`):
     ```bash
     ../../.venv/bin/python write_roi_tiffs.py --pred-dir output_new_batch [--keys ...|--all] [--views Bottom]
     ```
     → `output/roi_tiffs/<View>/<key>.tif` (use `--out-dir` to keep batches apart).

   Each TIFF holds the image, the predicted points as one multi-point selection, a read-only overlay naming each anchor where the CNN put it, and the image's calibration in µm. Image > Show Info lists the key, source, flags and the point order.

2. **In Fiji:** open the TIFF. The points appear as the active selection. With the **Multi-point tool**, drag each wrong point to its correct place. The overlay labels stay where the CNN put them, so you can see what you have moved (Image > Overlay > Hide Overlay hides them). Then **File > Save**, which keeps the selection in the TIFF.
   - If the selection is lost (e.g. you clicked outside it), close without saving and reopen. Or save it from the ROI Manager as `<key>.roi` next to the TIFF; that file is read instead.

3. **Read the corrections back.**
   ```bash
   ../../.venv/bin/python read_roi_tiffs.py                    # all TIFFs in output/roi_tiffs/
   ../../.venv/bin/python read_roi_tiffs.py --dry-run          # report only
   # lance new batch: add --pred-dir output_new_batch and the roi_tiffs folder path
   ```
   For each file it reports how many points moved and the largest move in µm, and writes `fiji_corrections.csv`, one row per image. Reading an image again replaces its row. Files where nothing moved are skipped (unless `--keep-unchanged`). It refuses a file whose point count or image doesn't match the predictions.

4. **Export again** (`export_geomorph.py`). Corrected images get source `<cnn source>+fiji` and pass QC. **A `drop` in `qc_review.csv` still wins**: change it to `keep` for images you have corrected. The export report lists any conflicts.

---

## 7. Output files

**Saw** (`genai_saw_landmarking/production/output/geomorph/`):

| File | Content |
|---|---|
| `Saw_v12_XY.csv` | one row per saw (female × side): `ID, side, cohort, species, host, treatment, colony, population, px_per_mm, cal_source, source, key, qc_flags, qc_pass, X1, Y1 … X52, Y52` in **mm**. Protocol frame: x right, y down, apex left, teeth up |
| `Saw_v12_sliders.csv` | `before, slide, after` for `gpagen(curves = …)` |
| `landmark_key_v12.csv` | column number → point: 1 `S01` apex; 2–8 `V1`–`V7`; 9–11 `T2`–`T4`; 12–18 `R1`–`R7`; 19–25 `D1`–`D7`; 26–46 ventral-curve semilandmarks; 47–52 rachis semilandmarks |
| `export_report.txt` | counts, missing metadata, duplicates, applied corrections/overrides |
| `PRIME_Saw_Pheno_v12.csv` | (from the R script) one row per female: centroid size, PCs, linear measures |

**Lance** (`<pred-dir>/geomorph/`):

| File | Content |
|---|---|
| `Lance<View>_v14_XY.csv` | `ID, species, group, session, px_per_mm, source, key, qc_flags, qc_pass, X1, Y1 … Xn, Yn` in **mm**, image axes |
| `Lance<View>_v14_sliders.csv` | slider matrix for `gpagen` |
| `landmark_key_v14.csv` | view, number → protocol point (e.g. Right 1 = `R01` apex, 18 = `R18` dorsal curve start) |
| `export_report.txt` | counts, duplicates, IDs without species |
| `PRIME_Lance<View>_Pheno_v14.csv` | (from the R script) centroid size, `Comp1`–`Comp20`, linear measures; joins to QTL tables by `ID` |

**Loading in R:**
```r
library(geomorph)
df <- read.csv("Saw_v12_XY.csv")
df <- df[df$qc_pass %in% c(TRUE, "TRUE"), ]
A  <- arrayspecs(df[, grep("^[XY][0-9]+$", names(df))], 52, 2)   # lance: 42 / 40 / 38
gpa <- gpagen(A, curves = as.matrix(read.csv("Saw_v12_sliders.csv")), ProcD = FALSE)
```

**Review images:** `output/overlays/` (JPEG, flagged or all) and `output/roi_tiffs/` (Fiji TIFFs with the points). For a figure of every image, run step S4 or L2 with `--overlays all`.

**Files you edit** (the scripts read them; never edit the generated CSVs):

| File | Pipeline | Purpose |
|---|---|---|
| `production/qc_review.csv` | both | keep/drop decisions |
| `production/fiji_corrections.csv` | both | written by `read_roi_tiffs.py`; delete a row to undo a correction |
| `production/metadata_overrides.csv` | saw | metadata for females not in PRIME, or corrections |
| `production/sample_sheet.csv` | lance | species for IDs the rules can't resolve |

---

## 8. Troubleshooting

| Symptom | Cause / fix |
|---|---|
| `ModuleNotFoundError: numpy` / `torch` | You are using the system Python. Use `.venv/bin/python` (§1) |
| TIFF won't open / `imagecodecs` error | Install `imagecodecs` (it's in `cnn/requirements.txt`) |
| `warning: N of 5 models found` / `in_sample` flags | Copy the missing `runs/.../<model>_f<k>/best.pt` and `split_keys.json` from MCC |
| A new saw is missing from `predictions_px_saw.csv` | It isn't under `<cohort>/raw_images/<session>/`, or it is an exact duplicate of another file (`duplicate_of` in `image_table.csv`). Rerun `prep_images.py` after adding images |
| Saw export crashes on `float('')` | An image has no calibration at all (`cal_source = none`). Rerun `tools/calibration_survey.py` after adding images; fix the images in `calibration_problems.csv` |
| Every point of a saw is mirrored or upside down | Wrong `_L`/`_R` in the file name. Rename and rerun `prep_images.py --overwrite` |
| A lance image is missing | Its name has no view letter: see `unparsed_images.txt` |
| A whole new batch is flagged `spread` or `shape` | The imaging differs from training (magnification, background, lighting, colour). Check a few overlays. If the points are good, keep them; if not, the models need retraining with labels from the new setup |
| Species or metadata empty in the export | Saw: add the ID to `metadata_overrides.csv`. Lance: add it to `sample_sheet.csv` or pass `--group` |
| A Fiji correction isn't used | The image is `drop` in `qc_review.csv` (set it to `keep`), or you didn't run `read_roi_tiffs.py` before exporting |
| `read_roi_tiffs.py` rejects a file | The point count changed (a point was added or deleted). Write the TIFF again and move points only |
