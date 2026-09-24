#!/bin/bash
# SLURM job array for the Morgan Compute Cluster (MCC, University of Kentucky):
# trains + evaluates one HeatmapNet per lance view (Bottom/Left/Right). Each
# array task is fully independent.
#
# MCC HAS NO GPUs (confirmed against MCC System Overview docs: standard
# nodes are AMD EPYC 7702P, 128 cores / 512GB RAM, no GPU hardware listed).
# This trains CPU-only, using many threads per node instead of a GPU.
#
# Before submitting:
#   1. Put this whole lance_landmarking/ project under YOUR SCRATCH space,
#      not $HOME -- MCC's $HOME quota is only 10GB, nowhere near enough for
#      the raw TIFF dataset (many GB). Use /scratch/linkblue/$USER/... and
#      transfer large data via the dedicated DTN (mcc-dtn.ccs.uky.edu) or
#      Globus, not the login node. Scratch is purged after 90 days of
#      inactivity and is not backed up -- keep your own copy of raw data
#      elsewhere.
#   2. Run setup_env.sh on a LOGIN node (needs internet) -- see that file.
#   3. mkdir -p logs   (SLURM needs this dir to exist before the job starts)
#   4. Edit every line marked EDIT below -- in particular -A (your project
#      account: run `sacctmgr show associations user=$USER` if unsure) and
#      the `module load` line for whatever the Anaconda module is actually
#      called on MCC (run `module avail anaconda` -- name shown in the SDS
#      catalog is just "Anaconda", exact module string wasn't confirmable
#      from the docs alone).
#
# Submit with:  sbatch train_lance_landmarks.slurm
# Re-run just one view with different settings, e.g.:
#   sbatch --array=2 --export=EPOCHS=150 train_lance_landmarks.slurm   # Right only

#SBATCH --job-name=lance-landmark
#SBATCH --array=0-2
#SBATCH --partition=normal            # MCC's documented partitions are "normal" and "jumbo" (jumbo = the 2 large-memory/4TB nodes -- not needed here)
#SBATCH --account=coa_cli242_uksr     # EDIT: required by MCC (-A); your project/allocation code
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=32            # out of 128/node -- raise if you have the node to yourself and want faster epochs, but be considerate on a shared cluster
#SBATCH --mem=64G                     # node has 512GB; the dataset + a few DataLoader workers' worth of decoded TIFFs is well under this
#SBATCH --time=14-00:00:00             # DD-HH:MM:SS per MCC docs, max 14-00:00:00; generous first-run estimate -- CPU training is slower per-image than GPU, tighten once you have real per-epoch timing from the logs
#SBATCH --mail-user=rdri228@uky.edu
#SBATCH --mail-type=ALL
#SBATCH --output=logs/%x_%A_%a.out
#SBATCH --error=logs/%x_%A_%a.err

set -euo pipefail

module load Miniconda3

# SLURM runs a COPY of this script from its spool dir (/var/spool/slurm/...),
# so BASH_SOURCE/$0 can't be used to locate the repo. $SLURM_SUBMIT_DIR is
# the directory sbatch was run from -- submit from lance_landmarking/cnn/.
MODEL_DIR="${SLURM_SUBMIT_DIR:?SLURM_SUBMIT_DIR not set}"
if [[ ! -f "$MODEL_DIR/train.py" ]]; then
    echo "ERROR: train.py not found in $MODEL_DIR -- run sbatch from lance_landmarking/cnn/" >&2
    exit 1
fi
REPO_ROOT="$(cd "$MODEL_DIR/../.." && pwd)"
ENV_DIR="$REPO_ROOT/.condaenv"           # created by setup_env.sh
source activate "$ENV_DIR"
cd "$MODEL_DIR"

# sbatch passes the SUBMITTING shell's environment to the job. If that shell
# already had this env active, `source activate` above can be a no-op and the
# module's base-Miniconda python ends up first on PATH (no matplotlib etc.).
# Don't depend on activation order: put the env first and call its python
# explicitly.
export PATH="$ENV_DIR/bin:$PATH"
PYTHON="$ENV_DIR/bin/python3"
[[ -x "$PYTHON" ]] || { echo "ERROR: $PYTHON not found -- run setup_env.sh" >&2; exit 1; }

echo "python: $PYTHON  ($($PYTHON --version 2>&1))"
if ! "$PYTHON" -c "import torch, torchvision, numpy, PIL, tifffile, imagecodecs, matplotlib"; then
    echo "ERROR: environment at $REPO_ROOT/.condaenv is missing packages -- rerun setup_env.sh or: pip install -r requirements.txt" >&2
    exit 1
fi

# no GPU: give PyTorch's intra-op (MKL/OpenMP) parallelism the CPUs SLURM
# actually gave this task, rather than however many the node happens to have
export PYTHONUNBUFFERED=1   # stdout to a file is block-buffered otherwise: epoch lines can lag by hours
export OMP_NUM_THREADS="$SLURM_CPUS_PER_TASK"
export MKL_NUM_THREADS="$SLURM_CPUS_PER_TASK"

ANGLES=(Bottom Left Right)
ANGLE="${ANGLES[$SLURM_ARRAY_TASK_ID]}"
# Defaults match what was validated locally on Right (batch 8, lr 1e-3, DSNT loss): held-out
# val error plateaued by ~epoch 8-12 with constant lr, so 40 epochs with cosine lr decay is plenty.
EPOCHS="${EPOCHS:-40}"
BATCH_SIZE="${BATCH_SIZE:-8}"
# 0 workers + --cache-images: each TIFF is decoded once (first epoch), then served from RAM,
# so all cores go to conv math instead of fighting DataLoader workers over decoding
NUM_WORKERS="${NUM_WORKERS:-0}"
# To continue an interrupted run, reuse its directory and set RESUME=1, e.g.:
#   sbatch --array=1 --export=ALL,RESUME=1,RUN_DIR=runs/left_36756021,EPOCHS=100 train_lance_landmarks.slurm
RUN_DIR="${RUN_DIR:-runs/${ANGLE,,}_${SLURM_ARRAY_JOB_ID}}"  # run folders are lower-case (snake_case)
RESUME_ARG=()
[[ -n "${RESUME:-}" ]] && RESUME_ARG=(--resume)
# Warm start from weights only (for runs made before per-epoch checkpoints existed):
#   INIT_WEIGHTS=runs/left_36756021/best.pt
[[ -n "${INIT_WEIGHTS:-}" ]] && RESUME_ARG+=(--init-weights "$INIT_WEIGHTS")

echo "host=$(hostname)  angle=$ANGLE  cpus=$SLURM_CPUS_PER_TASK  epochs=$EPOCHS  batch_size=$BATCH_SIZE  num_workers=$NUM_WORKERS"

"$PYTHON" train.py \
    --angle "$ANGLE" \
    --epochs "$EPOCHS" \
    --batch-size "$BATCH_SIZE" \
    --num-workers "$NUM_WORKERS" \
    --cache-images \
    --loss dsnt \
    --lr-decay cosine \
    --out-dir "$RUN_DIR" \
    ${RESUME_ARG[@]+"${RESUME_ARG[@]}"}

"$PYTHON" evaluate.py \
    --angle "$ANGLE" \
    --checkpoint "$RUN_DIR/best.pt" \
    --loss dsnt \
    --batch-size "$BATCH_SIZE"

echo "Done: $ANGLE -> $RUN_DIR"
