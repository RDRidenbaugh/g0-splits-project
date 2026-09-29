#!/usr/bin/env bash
# Round 2: predictions of the old/new/newdistal models on never-seen (hard) and test (easy) images.
REPO=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
LEGACY=${LEGACY_LANCE:-$HOME/g0-splits-archive/lance_landmarking}/cnn  # old-protocol manifests + runs (not in git)
R=$LEGACY/runs/protocol_comparison_r2
D=$REPO/genai_lance_landmarking/analysis/data/hard_r2
PY=$REPO/.venv/bin/python
for v in Right Left; do for p in old new newdistal; do for set in hard easy; do
  OMP_NUM_THREADS=${1:-4} $PY $REPO/genai_lance_landmarking/cnn/predict_images.py \
    --angle $v --checkpoint $R/${p}_${v,,}/best.pt \
    --manifest $REPO/genai_lance_landmarking/production/manifest_v2_images.csv \
    --keys $D/${v}_${set}_keys.txt --out $D/${v}_${p}_${set}_pred.csv
done; done; done
echo PRED DONE
