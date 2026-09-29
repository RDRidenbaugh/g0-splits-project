# ovipositor-genai-landmarking

Automated landmarking of *Neodiprion* ovipositors: protocols, CNN models, and geometric-morphometric export.

| Folder | What it holds |
|---|---|
| `cnn/` | Shared heatmap CNN (ResNet18 backbone, DSNT decoding): `train.py`, `evaluate.py`, model/data code, and `setup_env.sh` for the MCC conda environment. Both pipelines call it by path. |
| `genai_lance_landmarking/` | Lance protocol v1.4 (Right/Left/Bottom): protocol, autolabeling tools, and `production/` (cross-fitted models → mm XY for geomorph and the QTL phenotype table). |
| `genai_saw_landmarking/` | Saw protocol v1.2 (52 points): protocol, tools, and `production/` (cross-fitted models → geomorph export and morphometrics). `data/` holds the PRIME metadata tables. |

**To landmark new saw or lance images with the trained models, follow [`LANDMARKING_GUIDE.md`](LANDMARKING_GUIDE.md).** It covers everything from raw photos to the finished landmark tables, and how to read the QC flags.

Images, model checkpoints, and generated outputs are kept on disk, not in git (see `.gitignore`); each `production/README.md` lists what must be present. The PRIME metadata/phenotype tables and the R analysis scripts (including `saw_v12_morphometrics.R` and `lance_v14_morphometrics.R`) are unpublished and also kept on disk only, as are the `analysis/` folders (protocol comparisons, CNN validation, saw–lance analyses): this repository holds the CNN landmarking pipeline only.

The earlier human-digitized pipelines (`lance_landmarking/`, `saw_landmarking/`) were removed from the tree in the repository reframe and remain in git history. The finished v1.3 protocol-comparison scripts still read those old runs and derived manifests from `$LEGACY_LANCE` (default `~/g0-splits-archive/lance_landmarking`).
