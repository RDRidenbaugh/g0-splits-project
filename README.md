# ovipositor-genai-landmarking

Automated landmarking of *Neodiprion* ovipositors: protocols, CNN models, and geometric-morphometric export.

| Folder | What it holds |
|---|---|
| `cnn/` | Shared heatmap CNN (ResNet18 backbone, DSNT decoding): `train.py`, `evaluate.py`, model/data code, and `setup_env.sh` for the MCC conda environment. Both pipelines call it by path. |
| `genai_lance_landmarking/` | Lance protocol v1.4 (Right/Left/Bottom): protocol, autolabeling tools, protocol-comparison analyses, and `production/` (cross-fitted models → mm XY for geomorph and the QTL phenotype table). |
| `genai_saw_landmarking/` | Saw protocol v1.2 (52 points): protocol, tools, CNN validation, and `production/` (cross-fitted models → geomorph export and morphometrics). `data/` holds the PRIME metadata tables. |

Images, model checkpoints, and generated outputs are kept on disk, not in git (see `.gitignore`); each `production/README.md` lists what must be present.

The earlier human-digitized pipelines (`lance_landmarking/`, `saw_landmarking/`) were removed from the tree in the repository reframe and remain in git history. The finished v1.3 protocol-comparison scripts still read those old runs and derived manifests from `$LEGACY_LANCE` (default `~/g0-splits-archive/lance_landmarking`).
