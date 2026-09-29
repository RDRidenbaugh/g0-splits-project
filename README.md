# ovipositor-genai-landmarking

Automated landmarking of *Neodiprion* ovipositors: protocols, CNN models, and geometric-morphometric export.

| Folder | What it holds |
|---|---|
| `cnn/` | Shared heatmap CNN (ResNet18 backbone, DSNT decoding): `train.py`, `evaluate.py`, model/data code, and `setup_env.sh` for the MCC conda environment. Both pipelines call it by path. |
| `genai_lance_landmarking/` | Lance protocol v1.4 (Right/Left/Bottom): protocol, autolabeling tools, and `production/` (cross-fitted models → mm XY for geomorph and the QTL phenotype table). |
| `genai_saw_landmarking/` | Saw protocol v1.2 (52 points): protocol, tools, and `production/` (cross-fitted models → geomorph export and morphometrics). `data/` holds the PRIME metadata tables. |

**To landmark new saw or lance images with the trained models, follow [`LANDMARKING_GUIDE.md`](LANDMARKING_GUIDE.md).** It covers everything from raw photos to the finished landmark tables, and how to read the QC flags.
