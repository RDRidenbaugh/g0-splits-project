#!/bin/bash
# SLURM job array for MCC: the 5 production models for saw protocol v1.2
# (5 cross-fitting folds, folds by colony), each trained and then evaluated on its
# held-out fold. Same network code and settings as the lance v1.4 production models.
# Outputs: genai_saw_landmarking/production/runs/v12/saw_f<k>/{best.pt,split_keys.json,eval_test.json}
# Errors in eval_test.json are in px (mm come from each image's scale bar at landmarking;
# all saw sessions are 2140-2160 px/mm, so px / 2145 is within 0.5%).
#
# Setup (once): repo on scratch space, cnn/setup_env.sh -> .condaenv at the repo root,
# the #SBATCH --account line below; run `mkdir -p logs` here first.
# Images come from genai_saw_landmarking/production/images/ (made by prep_images.py:
# mirrored apex-left, colour-normalized; copy that folder to MCC, ~3.3 GB). The manifest
# paths are relative to this folder.
#
# Submit from genai_saw_landmarking/production/:   sbatch train_saw_v12_folds.slurm
# One fold only:  sbatch --array=2 train_saw_v12_folds.slurm
# Task id = fold 0-4.

#SBATCH --job-name=saw-v12
#SBATCH --array=0-4
#SBATCH --partition=normal            # MCC's documented partitions are "normal" and "jumbo" (jumbo = the 2 large-memory/4TB nodes -- not needed here)
#SBATCH --account=coa_cli242_uksr     # EDIT: required by MCC (-A); your project/allocation code
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=32            # out of 128/node -- raise if you have the node to yourself and want faster epochs, but be considerate on a shared cluster
#SBATCH --mem=64G                     # node has 512GB; the dataset + a few DataLoader workers' worth of decoded TIFFs is well under this
#SBATCH --time=12:00:00               # a 40-epoch DSNT run took 2.5-3.2 h at 32 CPUs (job 36764579)
#SBATCH --mail-user=rdri228@uky.edu
#SBATCH --mail-type=ALL
#SBATCH --output=logs/%x_%A_%a.out
#SBATCH --error=logs/%x_%A_%a.err

set -euo pipefail

module load Miniconda3

# SLURM runs a COPY of this script from its spool dir (/var/spool/slurm/...),
# so BASH_SOURCE/$0 can't be used to locate the repo. $SLURM_SUBMIT_DIR is
# the directory sbatch was run from -- submit from genai_saw_landmarking/production/.
PROD="${SLURM_SUBMIT_DIR:?SLURM_SUBMIT_DIR not set}"
if [[ ! -f "$PROD/manifest_saw_v12.csv" ]]; then
    echo "ERROR: manifest_saw_v12.csv not found in $PROD -- run sbatch from genai_saw_landmarking/production/" >&2
    exit 1
fi
# training/model code is shared with the old protocol; data, runs and logs stay in $PROD
MODEL_DIR="$(cd "$PROD/../../cnn" && pwd)"
REPO_ROOT="$(cd "$PROD/../.." && pwd)"
ENV_DIR="$REPO_ROOT/.condaenv"           # created by setup_env.sh
source activate "$ENV_DIR"
cd "$PROD"

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
    echo "ERROR: environment at $REPO_ROOT/.condaenv is missing packages -- rerun cnn/setup_env.sh or: pip install -r cnn/requirements.txt" >&2
    exit 1
fi

# no GPU: give PyTorch's intra-op (MKL/OpenMP) parallelism the CPUs SLURM
# actually gave this task, rather than however many the node happens to have
export PYTHONUNBUFFERED=1   # stdout to a file is block-buffered otherwise: epoch lines can lag by hours
export OMP_NUM_THREADS="$SLURM_CPUS_PER_TASK"
export MKL_NUM_THREADS="$SLURM_CPUS_PER_TASK"

ANGLE=Saw
FOLD=$SLURM_ARRAY_TASK_ID
EPOCHS="${EPOCHS:-40}"
RUN_DIR="runs/v12/saw_f${FOLD}"
mkdir -p "$RUN_DIR"
RESUME_ARG=()
[[ -f "$RUN_DIR/last.pt" ]] && RESUME_ARG=(--resume)

echo "host=$(hostname)  angle=$ANGLE  fold=$FOLD  cpus=$SLURM_CPUS_PER_TASK  epochs=$EPOCHS"

"$PYTHON" "$MODEL_DIR/train.py" \
    --angle "$ANGLE" \
    --manifest manifest_saw_v12.csv \
    --folds folds_saw_v12.json --fold "$FOLD" \
    --epochs "$EPOCHS" \
    --batch-size 8 \
    --num-workers 0 \
    --cache-images \
    --loss dsnt \
    --lr-decay cosine \
    --out-dir "$RUN_DIR" \
    ${RESUME_ARG[@]+"${RESUME_ARG[@]}"}

"$PYTHON" "$MODEL_DIR/evaluate.py" \
    --angle "$ANGLE" \
    --manifest manifest_saw_v12.csv \
    --folds folds_saw_v12.json --fold "$FOLD" \
    --checkpoint "$RUN_DIR/best.pt" \
    --loss dsnt \
    --out "$RUN_DIR/eval_test.json"

echo "Done: $ANGLE fold $FOLD -> $RUN_DIR"
