#!/usr/bin/env bash
# Afterlife nvidia-legacy bare-metal install (Ubuntu 24.04). UNTESTED recipe, written 2026-11-06.
# Reads state, changes system packages: run with --dry-run first. Needs sudo for driver/toolkit steps.
set -euo pipefail
DRIVER=580.196.07
DRIVER_URL=https://download.nvidia.com/XFree86/Linux-x86_64/${DRIVER}/NVIDIA-Linux-x86_64-${DRIVER}.run
LLAMA_COMMIT=fd27b2034905f8dadd8bd6d2cc44595f4929d391   # tag b12182
PREFIX=${AFTERLIFE_PREFIX:-$HOME/afterlife/nvidia-legacy}
DRY=0; [ "${1:-}" = "--dry-run" ] && DRY=1
run() { echo "+ $*"; [ $DRY -eq 1 ] || "$@"; }

echo "== 1. driver (R580). Skip if nvidia-smi already reports 580.x =="
cur=$(nvidia-smi --query-gpu=driver_version --format=csv,noheader 2>/dev/null | head -1 || true)
case "$cur" in 580.*) echo "driver $cur ok";; *)
  echo "Driver is '${cur:-none}'. Download+run manually (kernel module; reboot may be needed):"
  echo "  curl -fLO $DRIVER_URL && sudo sh NVIDIA-Linux-x86_64-${DRIVER}.run";;
esac

echo "== 2. CUDA 12.9.1 toolkit (NOT 13.x: CUDA 13 dropped sm_70/61) =="
run curl -fLO https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2404/x86_64/cuda-keyring_1.1-1_all.deb
run sudo dpkg -i cuda-keyring_1.1-1_all.deb
run sudo apt-get update
run sudo apt-get install -y cuda-toolkit-12-9 git cmake ninja-build build-essential python3-venv libcurl4-openssl-dev
export PATH=/usr/local/cuda-12.9/bin:$PATH

echo "== 3. llama.cpp b12182, CUDA arch 70;61 =="
run mkdir -p "$PREFIX"
[ -d "$PREFIX/llama.cpp" ] || run git clone https://github.com/ggml-org/llama.cpp.git "$PREFIX/llama.cpp"
run git -C "$PREFIX/llama.cpp" checkout "$LLAMA_COMMIT"
run cmake -S "$PREFIX/llama.cpp" -B "$PREFIX/build" -G Ninja -DGGML_CUDA=ON -DCMAKE_CUDA_ARCHITECTURES="70;61" -DCMAKE_BUILD_TYPE=Release
run cmake --build "$PREFIX/build" -j"$(nproc)"

echo "== 4. torch 2.14.0+cu126 venv (Python 3.12) =="
run python3 -m venv "$PREFIX/venv"
run "$PREFIX/venv/bin/pip" install torch==2.14.0 torchvision==0.29.0 --index-url https://download.pytorch.org/whl/cu126

echo "== 5. verify =="
run "$PREFIX/venv/bin/python" -c "import torch;print(torch.__version__, torch.cuda.is_available(), torch.cuda.get_device_capability(0))"
run "$PREFIX/build/bin/llama-cli" --version
echo "vLLM is a separate stack: see ../nvidia-legacy-vllm-1cat"
