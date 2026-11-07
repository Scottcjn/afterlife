#!/usr/bin/env bash
# Afterlife nvidia-legacy-vllm-1cat bare-metal install. UNTESTED, 2026-11-06. Requires R580 driver + CUDA 12.8 toolkit (nvcc) + Python 3.12.
set -euo pipefail
DRY=0; [ "${1:-}" = "--dry-run" ] && DRY=1
run() { echo "+ $*"; [ $DRY -eq 1 ] || "$@"; }
PREFIX=${AFTERLIFE_PREFIX:-$HOME/afterlife/vllm-1cat}
WHEEL_URL='https://github.com/1CatAI/1Cat-vLLM/releases/download/v1.5.2/1cat_vllm-1.5.2%2Bcu128-cp312-cp312-linux_x86_64.whl'
SHA=a27afc512cf29d4baa322366f92b32f1d0ddec6d7178b0bf4351ad00c1958baa
command -v nvcc >/dev/null || { echo "nvcc missing: install cuda-toolkit-12-8 (separate from the 12.9 used by nvidia-legacy; do not mix PATHs)"; [ $DRY -eq 1 ] || exit 1; }
run mkdir -p "$PREFIX"; [ $DRY -eq 1 ] || cd "$PREFIX"
run curl -fL -o 1cat.whl "$WHEEL_URL"
[ $DRY -eq 1 ] || echo "$SHA  1cat.whl" | sha256sum -c -
run python3.12 -m venv venv
run venv/bin/pip install ./1cat.whl
run venv/bin/python -c "import vllm;print(vllm.__version__)"
echo "Single-card smoke: serve a model that fits ONE card; 1Cat's published profiles assume 4xV100 TP4."
