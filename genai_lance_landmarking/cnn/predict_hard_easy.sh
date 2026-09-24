#!/usr/bin/env bash
# Predictions of the old- and new-protocol baseline models on the never-seen
# (hard) images and on the test split (easy), for the generalization check.
R=/home/labradorite/g0-splits-project/lance_landmarking/cnn/runs/protocol_comparison
D=/home/labradorite/g0-splits-project/genai_lance_landmarking/analysis/data/hard
PY=/home/labradorite/g0-splits-project/.venv/bin/python
for v in Right Left Bottom; do for p in old new; do for set in hard easy; do
  OMP_NUM_THREADS=${1:-2} $PY /home/labradorite/g0-splits-project/genai_lance_landmarking/cnn/predict_images.py \
    --angle $v --checkpoint $R/${p}_${v,,}/best.pt \
    --manifest /home/labradorite/g0-splits-project/lance_landmarking/cnn/manifest.csv \
    --keys $D/${v}_${set}_keys.txt --out $D/${v}_${p}_${set}_pred.csv
done; done; done
echo PRED DONE
