#!/usr/bin/env bash
# Local runner: trains the 15 production models (3 views x 5 cross-fitting folds) on protocol v1.4
# labels, each followed by its held-out-fold evaluation. Same settings as the protocol comparison
# (DSNT, cosine decay, 40 epochs, batch 8). Finished models are skipped, so rerunning resumes.
#   genai_lance_landmarking/production/runs/v14/<view>_f<k>/best.pt, split_keys.json, eval_test.json, run.log
# The training code is shared with the old protocol (lance_landmarking/cnn/*.py); data, runs and logs stay here.
# usage: bash train_folds.sh [parallel_jobs=3] [threads_per_job=3] [epochs=40]
# Local fallback; production training runs on MCC: train_v14_folds.slurm (same outputs).
set -u
P=${1:-3}; T=${2:-3}; E=${3:-40}
PROD=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
MODEL=$PROD/../../lance_landmarking/cnn
PY=/home/labradorite/g0-splits-project/.venv/bin/python
OUT=$PROD/runs/v14
mkdir -p "$OUT"
job() {
  view=$1; k=$2; d=$OUT/${view,,}_f$k
  [[ -f $d/eval_test.json ]] && { echo "skip $view fold $k (done)"; return; }
  mkdir -p "$d"; cd "$PROD" || exit 1
  resume=(); [[ -f $d/last.pt ]] && resume=(--resume)
  {
    echo "=== $view fold $k start $(date)"
    OMP_NUM_THREADS=$T $PY "$MODEL/train.py" --angle "$view" --manifest manifest_v14.csv --folds folds_v14.json --fold "$k" \
      --epochs "$E" --batch-size 8 --loss dsnt --lr-decay cosine --cache-images --num-workers 0 \
      --out-dir "$d" "${resume[@]}" &&
    OMP_NUM_THREADS=$T $PY "$MODEL/evaluate.py" --angle "$view" --manifest manifest_v14.csv --folds folds_v14.json --fold "$k" \
      --checkpoint "$d/best.pt" --loss dsnt --out "$d/eval_test.json"
    echo "=== $view fold $k end $(date) status $?"
  } >> "$d/run.log" 2>&1
  tail -n 1 "$d/run.log"
}
export -f job; export PROD MODEL PY OUT T E
for v in Right Left Bottom; do for k in 0 1 2 3 4; do echo "$v $k"; done; done |
  xargs -P "$P" -L 1 bash -c 'job $0 $1'
echo ALL DONE
