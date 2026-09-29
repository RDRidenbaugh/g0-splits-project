# Saw protocol v1.2: production CNN landmarking

Same design as the lance v1.4 production pipeline (`../../genai_lance_landmarking/production/`), with the same network code (`../../lance_landmarking/cnn/`, view name `Saw`, 52 points).

**Five cross-fitted models.** Folds are assigned by **colony**, so siblings never sit on both sides of a train/test split. The folds are balanced within cohort × species (g0/splits × lecontei/pinetum). An image whose label trained the models gets its held-out fold's model (out-of-fold); every other image gets the 5-model ensemble. No image is predicted by a model that saw it.

## Steps

1. **`python prep_images.py`** writes `images/<key>.tif` for every raw saw image (419; ~3.3 GB), and `image_table.csv`.
   - In the protocol frame (`../tools/frame.py`): apex left, teeth up. The image is mirrored left-right when needed so the apex points left, then flipped top to bottom. The orientation comes from the marked TIFF when there is one (410 images), otherwise from the filename's L/R.
   - Colour-normalized by the image's own background colour, so the green, pink, grey and white sessions look alike.
   - Same pixel grid as the raw image, so labels and predictions map back 1:1.
2. **`python make_production_data.py`** writes `manifest_saw_v12.csv` and `folds_saw_v12.json`. The manifest has **380 labelled images, 95% of the 399 unique images**: 311 autolabels that passed QC, plus 69 that failed QC but were marked "ok" in `../review/label_review.csv`. Labels marked "drop" are never used, and `landmark_source` says which route each label took. The 19 images without a label are still landmarked by the models (folds cover every image).
   - Exact duplicate raw files (18 stems, 20 copies: archive copies) are marked `duplicate_of` and skipped.
   - An image digitized twice (the BH/GK pairs) keeps one label.
3. **Train on MCC:** copy `images/`, the manifest and the folds to the repo on MCC, then from this folder run `mkdir -p logs && sbatch train_saw_v12_folds.slurm`. It's a 5-task array, one per fold; the lance models took about 3 h each at 32 CPUs. Models go to `runs/v12/saw_f<k>/`, and held-out errors in px to `eval_test.json`.
4. **`python landmark_images.py`** (local, about 10 min on CPU) predicts all 399 unique images: 380 out-of-fold and 19 by the 5-model ensemble. Output is `output/predictions_px_saw.csv` in prepared-image pixels (protocol frame), with QC flags (`label_gap`, `spread`, `order`, `outside`, `shape`, `no_scale`) and overlays of the flagged images in `output/overlays/`.
5. **`python export_geomorph.py`** writes `output/geomorph/Saw_v12_XY.csv`: one row per saw (ID × side), PRIME metadata, mm from each image's own scale bar, X1..Y52 in the protocol frame (x right, y down, apex left, teeth up). It also writes the slider matrix, the landmark key and an export report. PRIME IDs are matched by identical coordinates where the saw was digitized, otherwise by name. Decisions in `qc_review.csv` (key, decision = keep | drop) override the flags. Metadata for saws missing from the PRIME tables, or corrections, go in `metadata_overrides.csv` (ID, species, host, treatment, colony, population, note): every non-empty cell replaces the computed value for all saws of that female. Don't edit `Saw_v12_XY.csv` by hand, because each export rewrites it. `--out-dir` writes the export elsewhere, for example to compare with the current file.
6. **Optional, review in Fiji: `python write_roi_tiffs.py`** (flagged images; `--all` or `--keys ...` for others) writes `output/roi_tiffs/<key>.tif`. Each file holds the raw image in the protocol frame (`--prepared` gives the colour-normalized CNN input instead), the 52 predicted points as one multi-point ROI in `scheme.point_order()` order, an overlay naming the anchors at their CNN positions, and the image's own calibration in µm.
   To correct: drag the wrong points with the Multi-point tool (never add or delete one), then File > Save. **`python read_roi_tiffs.py`** reads the saved TIFFs back, reports which points moved and by how many µm, and records them in `fiji_corrections.csv` (one row per key; a re-read replaces the row). `export_geomorph.py` then uses the corrected points (source `<cnn source>+fiji`) and passes those images, unless `qc_review.csv` says drop. For an image you dropped and have now corrected, set its decision to keep.

**Validation (2026-09-27; `../analysis/prep_cnn_validation.py`, `cnn_validation.R`, `cnn_validation_modules.R`, `cnn_digitizer_host.R`).**
- **Held-out error:** mean about 6 µm per point, median about 4.7 µm. The apex, V1 and D2 are as good as a second human digitizer; the crowded distal points (R6–R7, D6–D7, V5–V7) are the weakest.
- **Against two people:** on the 14 images digitized by both BH and GK, the CNN is a median 5.0 / 5.4 µm from each, versus 2.0 µm between the two digitizers.
- **Repeatability,** label vs CNN on 380 images: shape R = 0.87, log centroid size R = 0.996. Measurement error is 6.6% of shape variance.
- **Biology on the same images:** species, pinetum diet and pinetum colony effects are equal for labels and CNN. Host in g0 lecontei is lower for the CNN (Z 6.1 vs 6.9 on 52 points; 5.8 vs 8.7 on the anchors). Part of the human host signal is a digitizer effect: after host, digitizer explains R² 0.065 (Z 5.5) of the human labels but 0.038 (Z 2.7) of the CNN. The host effect stays strongly significant in the CNN (Z 5.1 after digitizer).
- **Option if more precision is needed:** retrain on images cropped to the saw before shrinking, which roughly doubles effective resolution.

## Notes

- `evaluate.py` would take mm from the ImageJ calibration inside a marked TIFF. For the saws that is the old global 2160.7 px/mm, wrong for most sessions. So the manifest leaves `marked_tiff` empty and errors are in px. All saw sessions are 2140–2160 px/mm, so px / 2145 is within 0.5%.
- **Labels still to fix before the final training run:** `../review/label_review.csv`. It lists 82 QC failures with overlays, 9 undigitized images, 4 files with 33 points, and the BH/GK annulus-shift pair. Each correction adds a training label. Rerun steps 2–3 after corrections.
- **Smoke test (local, 2026-09-27):** 1 epoch on 24 images; `train.py` and `evaluate.py` both run on this manifest.
