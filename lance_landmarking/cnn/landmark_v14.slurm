#!/bin/bash
# SLURM job for MCC: landmark images with the 15 production v1.4 models and
# export geomorph-ready coordinates (landmark_images.py + export_geomorph.py).
# Same environment as train_v14_folds.slurm. Submit from lance_landmarking/cnn/.
#
# Whole mapping population, after training:
#   sbatch --dependency=afterok:<train array job id> landmark_v14.slurm
# A batch of new images (view read from the file names), into its own output folder:
#   sbatch --export=ALL,IMAGES=/scratch/.../new_batch,GROUP=PBX,OUT=/scratch/.../new_batch_out landmark_v14.slurm
# Outputs: <OUT>/predictions_px_<View>.csv, overlays/ (flagged images), geomorph/

#SBATCH --job-name=lance-v14-predict
#SBATCH --partition=normal            # MCC's documented partitions are "normal" and "jumbo" (jumbo = the 2 large-memory/4TB nodes -- not needed here)
#SBATCH --account=coa_cli242_uksr     # EDIT: required by MCC (-A); your project/allocation code
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=32            # out of 128/node -- raise if you have the node to yourself and want faster epochs, but be considerate on a shared cluster
#SBATCH --mem=64G                     # node has 512GB; the dataset + a few DataLoader workers' worth of decoded TIFFs is well under this
#SBATCH --time=06:00:00               # ~1000 TIFFs x 5 models; decoding dominates
#SBATCH --mail-user=rdri228@uky.edu
#SBATCH --mail-type=ALL
#SBATCH --output=logs/%x_%j.out
#SBATCH --error=logs/%x_%j.err


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

# The production models must all exist (runs/v14/<view>_f<k>/best.pt); a missing
# model would leave its held-out images predicted in-sample (flagged in_sample).
missing=0
for v in right left bottom; do for k in 0 1 2 3 4; do
  [[ -f runs/v14/${v}_f${k}/best.pt ]] || { echo "missing runs/v14/${v}_f${k}/best.pt" >&2; missing=1; }
done; done
(( missing )) && exit 1

PROD="$REPO_ROOT/genai_lance_landmarking/production"
OUT="${OUT:-$PROD/output}"
# IMAGES: space-separated folders/files; default = the whole mapping population
IMAGES="${IMAGES:-$REPO_ROOT/lance_landmarking/raw_images}"
EXTRA_ARGS=()
[[ -n "${GROUP:-}" ]] && EXTRA_ARGS+=(--group "$GROUP")
[[ -n "${PX_PER_MM:-}" ]] && EXTRA_ARGS+=(--px-per-mm "$PX_PER_MM")

echo "host=$(hostname)  cpus=$SLURM_CPUS_PER_TASK  images=$IMAGES  out=$OUT"
# shellcheck disable=SC2086  # IMAGES is deliberately word-split
"$PYTHON" "$PROD/landmark_images.py" $IMAGES --out-dir "$OUT" --workers 4 \
    ${EXTRA_ARGS[@]+"${EXTRA_ARGS[@]}"}
"$PYTHON" "$PROD/export_geomorph.py" --pred-dir "$OUT"
echo "Done -> $OUT/geomorph (copy it back and run lance_v14_morphometrics.R)"
