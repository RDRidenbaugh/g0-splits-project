#!/usr/bin/env bash
# Baseline CNN for the old-vs-new protocol comparison, run locally.
# Trains one model per (protocol, view) on the SAME images and splits
# (lance_landmarking/manifest_{oldproto_qc,newproto}.csv), with the settings of
# the 21ix26 MCC runs (DSNT loss, cosine decay, 40 epochs, batch 8), then
# evaluates on the test split and exports manual + predicted test landmarks.
# usage: bash run_protocol_comparison.sh [parallel_jobs=2] [threads_per_job=4]
set -u
P=${1:-2}; T=${2:-4}
MODEL=/home/labradorite/g0-splits-project/lance_landmarking/model
PY=/home/labradorite/g0-splits-project/.venv/bin/python
OUT=$MODEL/runs/protocol_comparison
DATA=/home/labradorite/g0-splits-project/novel_genai_landmarking_protocol/analysis/data/cnn
mkdir -p "$OUT" "$DATA"
job() {
  proto=$1; view=$2
  man=$MODEL/../manifest_${proto}.csv; [ "$proto" = old ] && man=$MODEL/../manifest_oldproto_qc.csv
  [ "$proto" = new ] && man=$MODEL/../manifest_newproto.csv
  d=$OUT/${proto}_${view}
  mkdir -p "$d"
  cd "$MODEL" || exit 1
  {
    echo "=== $proto $view start $(date)"
    OMP_NUM_THREADS=$T $PY train.py --angle "$view" --manifest "$man" --epochs 40 --batch-size 8 \
      --loss dsnt --lr-decay cosine --cache-images --num-workers 0 --out-dir "$d" &&
    OMP_NUM_THREADS=$T $PY evaluate.py --angle "$view" --manifest "$man" --checkpoint "$d/best.pt" \
      --loss dsnt --out "$d/eval_test.json" &&
    OMP_NUM_THREADS=$T $PY export_predictions.py --angle "$view" --manifest "$man" --checkpoint "$d/best.pt" \
      --out-dir "$DATA" --suffix "_${proto}proto"
    echo "=== $proto $view end $(date) status $?"
  } > "$d/run.log" 2>&1
  tail -1 "$d/run.log"
}
export -f job; export MODEL PY OUT DATA T
printf "%s\n" "new Right" "old Right" "new Left" "old Left" "new Bottom" "old Bottom" |
  xargs -P "$P" -L 1 bash -c 'job $0 $1'
echo ALL DONE
