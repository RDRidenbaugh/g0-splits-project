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
#SBATCH --account=YOUR_ACCOUNT        # EDIT: required by MCC (-A); your project/allocation code
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=32            # out of 128/node -- raise if you have the node to yourself and want faster epochs, but be considerate on a shared cluster
#SBATCH --mem=64G                     # node has 512GB; the dataset + a few DataLoader workers' worth of decoded TIFFs is well under this
#SBATCH --time=1-00:00:00             # DD-HH:MM:SS per MCC docs, max 14-00:00:00; generous first-run estimate -- CPU training is slower per-image than GPU, tighten once you have real per-epoch timing from the logs
#SBATCH --output=logs/%x_%A_%a.out
#SBATCH --error=logs/%x_%A_%a.err

set -euo pipefail

# EDIT: exact Anaconda module name/version -- check `module avail anaconda` on MCC first
module load anaconda3

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
source activate "$REPO_ROOT/.condaenv"   # created by setup_env.sh
cd "$REPO_ROOT/lance_landmarking/model"

# no GPU: give PyTorch's intra-op (MKL/OpenMP) parallelism the CPUs SLURM
# actually gave this task, rather than however many the node happens to have
export OMP_NUM_THREADS="$SLURM_CPUS_PER_TASK"
export MKL_NUM_THREADS="$SLURM_CPUS_PER_TASK"

ANGLES=(Bottom Left Right)
ANGLE="${ANGLES[$SLURM_ARRAY_TASK_ID]}"
EPOCHS="${EPOCHS:-100}"
BATCH_SIZE="${BATCH_SIZE:-16}"
# keep worker count modest -- most cores should go to conv math (OMP_NUM_THREADS
# above) inside the one training process, not to parallel data loading;
# too many DataLoader workers just fights the main process for the same cores
NUM_WORKERS="${NUM_WORKERS:-4}"
RUN_DIR="runs/${ANGLE}_${SLURM_ARRAY_JOB_ID}"

echo "host=$(hostname)  angle=$ANGLE  cpus=$SLURM_CPUS_PER_TASK  epochs=$EPOCHS  batch_size=$BATCH_SIZE  num_workers=$NUM_WORKERS"

python3 train.py \
    --angle "$ANGLE" \
    --epochs "$EPOCHS" \
    --batch-size "$BATCH_SIZE" \
    --num-workers "$NUM_WORKERS" \
    --out-dir "$RUN_DIR"

python3 evaluate.py \
    --angle "$ANGLE" \
    --checkpoint "$RUN_DIR/best.pt" \
    --batch-size "$BATCH_SIZE"

echo "Done: $ANGLE -> $RUN_DIR"
