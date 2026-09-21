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
module load Miniconda3

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ENV_DIR="$REPO_ROOT/.condaenv"

echo "!!! Make sure $REPO_ROOT is under /scratch/linkblue/\$USER/... !!!"
echo "    (MCC \$HOME quota is 10GB -- the raw TIFF dataset alone will not fit)"
echo

# Python >=3.12 is required: numpy 2.5.x, tifffile 2026.x and imagecodecs 2026.x
# publish no wheels for 3.11 (verified with `pip download --python-version`).
# -y also overwrites a leftover env from an earlier failed run at this path.
# Don't rebuild an env that this shell currently has active.
if [[ "${CONDA_PREFIX:-}" == "$ENV_DIR" ]]; then
    echo "ERROR: $ENV_DIR is active in this shell. Run 'conda deactivate' (repeat until the prompt prefix is gone), then rerun." >&2
    exit 1
fi

echo "Creating conda env at $ENV_DIR"
conda create -y --prefix "$ENV_DIR" python=3.12

# Use the new env's interpreter by full path for everything below. A bare
# `pip`/`python3` resolves via PATH, and `module load Miniconda3` can put the
# base Miniconda (an older Python) ahead of the env -- which is how a base
# pip ended up unable to see torch >2.8 and failing on numpy/torch pins.
PYTHON="$ENV_DIR/bin/python3"
echo "Env python: $($PYTHON --version 2>&1) at $PYTHON"
"$PYTHON" -c 'import sys; assert sys.version_info >= (3, 12), sys.version' \
    || { echo "ERROR: env python is older than 3.12" >&2; exit 1; }

echo "Installing PyTorch (CPU build -- MCC has no GPUs)"
# same pins as requirements.txt so the next step finds them already satisfied
"$PYTHON" -m pip install --index-url https://download.pytorch.org/whl/cpu torch==2.14.0 torchvision==0.29.0

echo "Installing remaining dependencies"
"$PYTHON" -m pip install -r "$REPO_ROOT/lance_landmarking/model/requirements.txt"

echo "Pre-downloading pretrained ResNet18 weights (needs internet -- do this here, not in the SLURM job)"
"$PYTHON" -c "
import torchvision
torchvision.models.resnet18(weights=torchvision.models.ResNet18_Weights.DEFAULT)
print('cached to', __import__('torch').hub.get_dir())
"

echo "Done. Env: $ENV_DIR  (train_lance_landmarks.slurm calls its python directly)"
