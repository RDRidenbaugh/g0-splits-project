# Production landmarking, protocol v1.4

This pipeline goes from raw lance TIFFs to geomorph-ready coordinates in mm and a phenotype table for QTL mapping.

## Models

There are 15 CNNs: 3 views × 5 cross-fitting folds. They are trained on the v1.4 automatic labels that passed QC (Right 273, Left 265, Bottom 238 images).

Folds are assigned by family and balanced within each cross type, so siblings never sit on both sides of a train/test split.

Everything for v1.4 lives in this folder: training data (`manifest_v14.csv`, `folds_v14.json`), SLURM scripts, `runs/`, `logs/` and `output/`. It reads the images from `genai_lance_landmarking/raw_images/` and `landmarked_images/`, so nothing is written to `lance_landmarking/`. Only the network code (`lance_landmarking/cnn/train.py`, `evaluate.py`, `model.py`, `dataset.py`) is shared, and it is called by path.

Training runs on MCC, with the same environment as the earlier runs (`lance_landmarking/cnn/setup_env.sh`, `.condaenv` at the repo root on scratch).

1. **Locally, only if the labels change:**
   ```
   python make_production_data.py
   ```
   It writes `manifest_v14.csv` and `folds_v14.json` here. Both are committed, so MCC gets them with the code.
2. **On MCC, in the repo on scratch:**
   - Check out this branch (`git fetch && git checkout lance-cnn-production`), or copy the changed files.
   - Make sure `genai_lance_landmarking/raw_images/` is there (`raw_images/lbx/…`, the same 968 files as `lance_landmarking/raw_images/`). Training reads only the raw images; the manifest paths are relative to this folder. To avoid storing 9.5 GB twice on scratch, a symlink works: `ln -s ../lance_landmarking/raw_images genai_lance_landmarking/raw_images`.
   - Run `setup_env.sh` again only if `.condaenv` is missing.
3. **Submit, from `genai_lance_landmarking/production/`:**
   ```
   mkdir -p logs
   sbatch train_v14_folds.slurm                                  # 15 tasks: 0-4 Right, 5-9 Left, 10-14 Bottom folds
   sbatch --dependency=afterok:<array job id> landmark_v14.slurm # landmarks the whole population + exports
   ```
   Each model takes about 3 hours at 32 CPUs. A rerun of a task resumes from its `last.pt`. To rerun one model: `sbatch --array=7 train_v14_folds.slurm`.
4. **Copy `genai_lance_landmarking/production/output/` back.** Then review the overlays and run `lance_v14_morphometrics.R` locally.

Outputs go to `runs/v14/<view>_f<k>/` in this folder. Each run folder has `best.pt`, `split_keys.json`, and `eval_test.json`, the error on its held-out fold. `train_folds.sh` does the same training on a local machine; it takes about 20 hours on a laptop.

**New image batches on MCC:**
```
sbatch --export=ALL,IMAGES=/scratch/.../batch3,GROUP=PBX,OUT=/scratch/.../batch3_out landmark_v14.slurm
```

**Held-out error of the production models** (MCC job 36849347; every labelled image, predicted once by the model that never saw it):

| View | Images | Mean | Median | 90th percentile |
|---|---|---|---|---|
| Right | 273 | 11.3 µm | 10.4 µm | 16.0 µm |
| Left | 265 | 11.7 µm | 10.5 µm | 16.3 µm |
| Bottom | 238 | 15.7 µm | 13.5 µm | 25.3 µm |

These errors are measured against the automatic labels. The largest are on the heel (R02/R03, L02/L03) and at the Bottom shoulders (B12/B13).

## Landmarking

Locally, or on MCC through `landmark_v14.slurm`:
```
python landmark_images.py                                  # whole mapping population (genai_lance_landmarking/raw_images)
python landmark_images.py /path/to/new_images --group PBX  # new images; the view comes from the file name
python export_geomorph.py                                  # -> output/geomorph/
Rscript lance_v14_morphometrics.R                          # -> output/geomorph/PRIME_Lance<View>_Pheno_v14.csv
```

**No image is predicted by a model that trained on it.** An image whose label was used in training gets the model for which it was held out (source `oof_f<k>`). Every other image gets the mean of the five models (source `ensemble`). This covers images that failed label QC, images never digitized, and new images. The whole population is therefore phenotyped the same way.

**Calibration** is read per image, in this order:
1. `--px-per-mm`, if given.
2. The calibration NIS-Elements writes into its TIFFs. The 2560×1920 images were taken on a Nikon DS-Fi2-U3 on the SMZ at 3.00× zoom and read 1321.9 px/mm; their 200 µm bar is 264 px.
3. Otherwise, the image width. The 3840×2160 files carry no calibration; their 1 mm bar is 926–929 px, so 927 px/mm.

The ImageJ calibration stored in the marked 2560×1920 TIFFs, 1260 px/mm, is about 5% low: it disagrees with both the NIS value and the scale bar. It is not used.

Every image's red scale bar is also measured. It must come out a round length (10 µm to 5 mm, within 1.5%) under the calibration used; otherwise the image is flagged `scale_bar`, or `no_bar` if no bar is found. This catches a changed zoom or a wrong calibration in new batches.

**QC flags:**

| Flag | Meaning |
|---|---|
| `spread` | The 5 models disagree (only meaningful for `ensemble` images) |
| `label_gap` | A held-out prediction is far from the image's own v1.4 label (over 21 µm lateral, 27 µm Bottom). The CNN or the label is wrong; the overlay draws both, with the label in cyan |
| `order` | Sutures are out of order along the axis |
| `outside` | A point falls outside the image |
| `shape` | The individual is a Procrustes outlier |
| `no_scale` | No calibration was found |
| `scale_bar` | The burned-in scale bar is not a round length under the calibration used |
| `no_bar` | No red scale bar was found |
| `in_sample` | The model that should have held this image out is missing |

Flagged images get an overlay in `output/overlays/<View>/`. To override a flag, add a row to `qc_review.csv` with `view,key,decision,note`, where `decision` is `keep` or `drop`. Then rerun `export_geomorph.py`.

**Species** comes from `sample_sheet.csv` (the IDs in the old coordinate tables). If an ID is missing there, it comes from the cross type, or from the ID prefix for parents (LL/LX = Lecontei, NP/PX = Pinetum). `export_report.txt` lists any IDs it could not resolve.

## Files for geomorph (`output/geomorph/`)

- **`Lance<View>_v14_XY.csv`:** `ID, species, group, session, px_per_mm, source, key, qc_flags, qc_pass`, then `X1, Y1, …, Xn, Yn` in mm, in image axes. This matches the PRIME saw tables:
  ```r
  arrayspecs(df[, grep("^[XY][0-9]+$", names(df))], n, 2)
  gpagen(A, curves = as.matrix(read.csv("Lance<View>_v14_sliders.csv")), ProcD = FALSE)
  ```
- **`landmark_key_v14.csv`:** maps each column number to its protocol point (e.g. Right 18 = R18, the dorsal curve start). The linear measures in `lance_v14_morphometrics.R` use these numbers.
- **`PRIME_Lance<View>_Pheno_v14.csv`:** `ID, species, session, centroid_size_<view>, Comp1–Comp20`, then the linear measures of protocol §6.2 in mm and degrees. It joins to the QTL tables by `ID`, like `PRIME_Lance<View>_Pheno_v3.csv`.
  - **Lateral views:** window length, suture lengths and angles, ventral and dorsal suture spacing, scallop amplitude, face length, blade chord, heel length, ventral and dorsal arc lengths, heights to the dorsal edge, and band height ("cutting depth").
  - **Bottom:** half lengths, fork depth, inner and tip-divergence angles, along-axis lengths, apex offset, shoulder span, position and asymmetry, widths at sutures 1–4, shaft taper, and tip and side arc lengths.
