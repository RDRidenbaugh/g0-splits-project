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
4. *(to build)* **Landmark every image** with the out-of-fold / ensemble rule, then write the mm export for geomorph using each image's own scale bar (`../analysis/data/calibration.csv`), un-mirrored side recorded, plus QC flags and overlays, as in the lance pipeline.

## Notes

- `evaluate.py` would take mm from the ImageJ calibration inside a marked TIFF. For the saws that is the old global 2160.7 px/mm, wrong for most sessions. So the manifest leaves `marked_tiff` empty and errors are in px. All saw sessions are 2140–2160 px/mm, so px / 2145 is within 0.5%.
- **Labels still to fix before the final training run:** `../review/label_review.csv`. It lists 82 QC failures with overlays, 9 undigitized images, 4 files with 33 points, and the BH/GK annulus-shift pair. Each correction adds a training label. Rerun steps 2–3 after corrections.
- **Smoke test (local, 2026-09-27):** 1 epoch on 24 images; `train.py` and `evaluate.py` both run on this manifest.
