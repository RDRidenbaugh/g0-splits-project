# Production landmarking, protocol v1.4

This pipeline goes from raw lance TIFFs to geomorph-ready coordinates in mm and a phenotype table for QTL mapping.

## Models

There are 15 CNNs: 3 views × 5 cross-fitting folds. They are trained on the v1.4 automatic labels that passed QC (Right 273, Left 265, Bottom 238 images).

Folds are assigned by family and balanced within each cross type, so siblings never sit on both sides of a train/test split.

```
python make_production_data.py        # -> lance_landmarking/cnn/manifest_v14.csv, folds_v14.json
bash train_folds.sh 3 3 40            # local: 3 models at a time; rerun resumes; about 20 h in total
# or on MCC, from lance_landmarking/cnn/:  sbatch train_v14_folds.slurm   (about 30 min per model)
```

Outputs go to `lance_landmarking/cnn/runs/v14/<view>_f<k>/`. Each run folder has `best.pt`, `split_keys.json`, and `eval_test.json`, the error on its held-out fold.

## Landmarking

```
python landmark_images.py                                  # whole mapping population (lance_landmarking/raw_images)
python landmark_images.py /path/to/new_images --group PBX  # new images; the view comes from the file name
python export_geomorph.py                                  # -> output/geomorph/
Rscript lance_v14_morphometrics.R                          # -> output/geomorph/PRIME_Lance<View>_Pheno_v14.csv
```

**No image is predicted by a model that trained on it.** An image whose label was used in training gets the model for which it was held out (source `oof_f<k>`). Every other image gets the mean of the five models (source `ensemble`). This covers images that failed label QC, images never digitized, and new images. The whole population is therefore phenotyped the same way.

**Calibration** is set by image width: 3840 px = 927 px/mm and 2560 px = 1260 px/mm, matching the two cameras' ImageJ calibrations. Pass `--px-per-mm` for a new camera.

**QC flags:**

| Flag | Meaning |
|---|---|
| `spread` | The 5 models disagree |
| `order` | Sutures are out of order along the axis |
| `outside` | A point falls outside the image |
| `shape` | The individual is a Procrustes outlier |
| `no_scale` | No calibration was found |
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
