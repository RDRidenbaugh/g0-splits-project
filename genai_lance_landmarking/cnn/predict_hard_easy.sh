#!/usr/bin/env bash
# Predictions of the old- and new-protocol baseline models on the never-seen
# (hard) images and on the test split (easy), for the generalization check.
REPO=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
LEGACY=${LEGACY_LANCE:-$HOME/g0-splits-archive/lance_landmarking}/cnn  # old-protocol manifests + runs (not in git)
R=$LEGACY/runs/protocol_comparison
D=$REPO/genai_lance_landmarking/analysis/data/hard
PY=$REPO/.venv/bin/python
for v in Right Left Bottom; do for p in old new; do for set in hard easy; do
  OMP_NUM_THREADS=${1:-2} $PY $REPO/genai_lance_landmarking/cnn/predict_images.py \
    --angle $v --checkpoint $R/${p}_${v,,}/best.pt \
    --manifest $REPO/genai_lance_landmarking/production/manifest_v2_images.csv \
    --keys $D/${v}_${set}_keys.txt --out $D/${v}_${p}_${set}_pred.csv
done; done; done
echo PRED DONE
