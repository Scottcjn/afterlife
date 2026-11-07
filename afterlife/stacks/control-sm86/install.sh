#!/usr/bin/env bash
# Afterlife control-sm86 bare-metal install. UNTESTED, 2026-11-06. Driver install is manual (see stack.yaml).
set -euo pipefail
DRY=0; [ "${1:-}" = "--dry-run" ] && DRY=1
run() { echo "+ $*"; [ $DRY -eq 1 ] || "$@"; }
PREFIX=${AFTERLIFE_PREFIX:-$HOME/afterlife/control-sm86}
run curl -fLO https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2404/x86_64/cuda-keyring_1.1-1_all.deb
run sudo dpkg -i cuda-keyring_1.1-1_all.deb
run sudo apt-get update
run sudo apt-get install -y cuda-toolkit-13-4 git cmake ninja-build build-essential python3-venv libcurl4-openssl-dev
export PATH=/usr/local/cuda-13.4/bin:$PATH
run mkdir -p "$PREFIX"
[ -d "$PREFIX/llama.cpp" ] || run git clone https://github.com/ggml-org/llama.cpp.git "$PREFIX/llama.cpp"
run git -C "$PREFIX/llama.cpp" checkout fd27b2034905f8dadd8bd6d2cc44595f4929d391
run cmake -S "$PREFIX/llama.cpp" -B "$PREFIX/build" -G Ninja -DGGML_CUDA=ON -DCMAKE_CUDA_ARCHITECTURES=86 -DCMAKE_BUILD_TYPE=Release
run cmake --build "$PREFIX/build" -j"$(nproc)"
run python3 -m venv "$PREFIX/venv"
run "$PREFIX/venv/bin/pip" install torch==2.15.0
run "$PREFIX/venv/bin/python" -c "import torch;print(torch.__version__, torch.cuda.get_device_capability(0))"
