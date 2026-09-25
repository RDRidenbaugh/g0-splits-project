#!/bin/bash
# SLURM job array for MCC: the 15 production models for protocol v1.4
# (3 views x 5 cross-fitting folds), each trained and then evaluated on its
# held-out fold. Local equivalent: genai_lance_landmarking/production/train_folds.sh.
# Outputs: runs/v14/<view>_f<k>/{best.pt,split_keys.json,eval_test.json}
#
# Setup is the same as train_lance_landmarks.slurm (scratch space, setup_env.sh,
# mkdir -p logs, account line). manifest_v14.csv and folds_v14.json must be here,
# and raw_images/ must sit beside cnn/ (the manifest's paths are relative).
#
# Submit from lance_landmarking/cnn/:   sbatch train_v14_folds.slurm
# Only some models, e.g. Bottom folds:  sbatch --array=10-14 train_v14_folds.slurm
# Task id -> view/fold: 0-4 Right f0-f4, 5-9 Left f0-f4, 10-14 Bottom f0-f4.

#SBATCH --job-name=lance-v14
#SBATCH --array=0-14
#SBATCH --partition=normal            # MCC's documented partitions are "normal" and "jumbo" (jumbo = the 2 large-memory/4TB nodes -- not needed here)
#SBATCH --account=coa_cli242_uksr     # EDIT: required by MCC (-A); your project/allocation code
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=32            # out of 128/node -- raise if you have the node to yourself and want faster epochs, but be considerate on a shared cluster
#SBATCH --mem=64G                     # node has 512GB; the dataset + a few DataLoader workers' worth of decoded TIFFs is well under this
#SBATCH --time=1-00:00:00             # a 40-epoch DSNT run took ~22 min at 32 CPUs (job 36764579); generous margin
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

VIEWS=(Right Left Bottom)
ANGLE="${VIEWS[$((SLURM_ARRAY_TASK_ID / 5))]}"
FOLD=$((SLURM_ARRAY_TASK_ID % 5))
EPOCHS="${EPOCHS:-40}"
RUN_DIR="runs/v14/${ANGLE,,}_f${FOLD}"
mkdir -p "$RUN_DIR"
RESUME_ARG=()
[[ -f "$RUN_DIR/last.pt" ]] && RESUME_ARG=(--resume)

echo "host=$(hostname)  angle=$ANGLE  fold=$FOLD  cpus=$SLURM_CPUS_PER_TASK  epochs=$EPOCHS"

"$PYTHON" train.py \
    --angle "$ANGLE" \
    --manifest manifest_v14.csv \
    --folds folds_v14.json --fold "$FOLD" \
    --epochs "$EPOCHS" \
    --batch-size 8 \
    --num-workers 0 \
    --cache-images \
    --loss dsnt \
    --lr-decay cosine \
    --out-dir "$RUN_DIR" \
    ${RESUME_ARG[@]+"${RESUME_ARG[@]}"}

"$PYTHON" evaluate.py \
    --angle "$ANGLE" \
    --manifest manifest_v14.csv \
    --folds folds_v14.json --fold "$FOLD" \
    --checkpoint "$RUN_DIR/best.pt" \
    --loss dsnt \
    --out "$RUN_DIR/eval_test.json"

echo "Done: $ANGLE fold $FOLD -> $RUN_DIR"
