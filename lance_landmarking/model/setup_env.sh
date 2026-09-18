#!/usr/bin/env bash
# One-time environment setup for the lance-landmarking CNN pipeline, for the
# Morgan Compute Cluster (MCC).
#
# Run this on a LOGIN node (needs internet), NOT inside a SLURM job --
# compute-node internet access isn't documented/confirmed for MCC, and this
# script both installs packages from PyPI and pre-downloads pretrained
# ResNet18 weights that train.py needs at runtime, so do it here regardless.
#
# MCC has no GPUs (see train_lance_landmarks.slurm header) -- this installs
# plain CPU PyTorch, same build validated in local dev, no CUDA index needed.
#
# Usage: bash setup_env.sh
set -euo pipefail

# EDIT: exact Anaconda module name/version on MCC -- run `module avail anaconda` first
module load anaconda3

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ENV_DIR="$REPO_ROOT/.condaenv"

echo "!!! Make sure $REPO_ROOT is under /scratch/linkblue/\$USER/... !!!"
echo "    (MCC \$HOME quota is 10GB -- the raw TIFF dataset alone will not fit)"
echo

echo "Creating conda env at $ENV_DIR"
conda create -y --prefix "$ENV_DIR" python=3.11
source activate "$ENV_DIR"

echo "Installing PyTorch (CPU build -- MCC has no GPUs)"
pip install --index-url https://download.pytorch.org/whl/cpu torch torchvision

echo "Installing remaining dependencies"
pip install -r "$REPO_ROOT/lance_landmarking/model/requirements.txt"

echo "Pre-downloading pretrained ResNet18 weights (needs internet -- do this here, not in the SLURM job)"
python3 -c "
import torchvision
torchvision.models.resnet18(weights=torchvision.models.ResNet18_Weights.DEFAULT)
print('cached to', __import__('torch').hub.get_dir())
"

echo "Done. Compute nodes just need: module load anaconda3 && source activate $ENV_DIR"
