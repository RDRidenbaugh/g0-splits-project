#!/usr/bin/env bash
# Round 2 of the protocol comparison (Right and Left): after the dorsal-curve label fix.
# Three models per face on the SAME corrected image set and splits:
#   old       - v2 human points                     (lance_landmarking/manifest_r2_old.csv)
#   new       - v1.3 labels, corrected dorsal start (manifest_r2_new.csv)
#   newdistal - v1.3 labels, dorsal curve starting at the window's proximal end (manifest_r2_newdistal.csv)
# Same settings as round 1 (DSNT, cosine decay, 40 epochs, batch 8); then test evaluation + export.
# usage: bash run_round2.sh [parallel_jobs=3] [threads_per_job=3]
set -u
P=${1:-3}; T=${2:-3}
MODEL=/home/labradorite/g0-splits-project/lance_landmarking/model
PY=/home/labradorite/g0-splits-project/.venv/bin/python
OUT=$MODEL/runs/protocol_comparison_r2
DATA=/home/labradorite/g0-splits-project/novel_genai_landmarking_protocol/analysis/data/cnn_r2
mkdir -p "$OUT" "$DATA"
job() {
  tag=$1; view=$2; man=$MODEL/../manifest_r2_${tag}.csv; d=$OUT/${tag}_${view}
  mkdir -p "$d"; cd "$MODEL" || exit 1
  {
    echo "=== $tag $view start $(date)"
    OMP_NUM_THREADS=$T $PY train.py --angle "$view" --manifest "$man" --epochs 40 --batch-size 8 \
      --loss dsnt --lr-decay cosine --cache-images --num-workers 0 --out-dir "$d" &&
    OMP_NUM_THREADS=$T $PY evaluate.py --angle "$view" --manifest "$man" --checkpoint "$d/best.pt" \
      --loss dsnt --out "$d/eval_test.json" &&
    OMP_NUM_THREADS=$T $PY export_predictions.py --angle "$view" --manifest "$man" --checkpoint "$d/best.pt" \
      --out-dir "$DATA" --suffix "_${tag}proto"
    echo "=== $tag $view end $(date) status $?"
  } > "$d/run.log" 2>&1
  tail -n 1 "$d/run.log"
}
export -f job; export MODEL PY OUT DATA T
printf "%s\n" "old Right" "new Right" "newdistal Right" "old Left" "new Left" "newdistal Left" |
  xargs -P "$P" -L 1 bash -c 'job $0 $1'
echo ALL DONE
