#!/usr/bin/env bash
# Round 2: predictions of the old/new/newdistal models on never-seen (hard) and test (easy) images.
R=/home/labradorite/g0-splits-project/lance_landmarking/model/runs/protocol_comparison_r2
D=/home/labradorite/g0-splits-project/novel_genai_landmarking_protocol/analysis/data/hard_r2
PY=/home/labradorite/g0-splits-project/.venv/bin/python
for v in Right Left; do for p in old new newdistal; do for set in hard easy; do
  OMP_NUM_THREADS=${1:-4} $PY /home/labradorite/g0-splits-project/novel_genai_landmarking_protocol/cnn/predict_images.py \
    --angle $v --checkpoint $R/${p}_$v/best.pt \
    --manifest /home/labradorite/g0-splits-project/lance_landmarking/manifest.csv \
    --keys $D/${v}_${set}_keys.txt --out $D/${v}_${p}_${set}_pred.csv
done; done; done
echo PRED DONE
