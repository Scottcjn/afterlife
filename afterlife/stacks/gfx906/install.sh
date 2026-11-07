#!/usr/bin/env bash
# Afterlife gfx906 bare-metal install (Ubuntu 24.04). UNTESTED recipe, 2026-11-06.
# Usage: install.sh [--dry-run] [--with-torch] [--legacy-6.4.4]
# Will REFUSE if AMD's official ROCm apt repo is configured (conflicts with the gfx906 repo).
set -euo pipefail
DRY=0; TORCH=0; LEGACY=0
for a in "$@"; do case $a in --dry-run) DRY=1;; --with-torch) TORCH=1;; --legacy-6.4.4) LEGACY=1;; esac; done
run() { echo "+ $*"; [ $DRY -eq 1 ] || "$@"; }
ROCM_BUILD=7.14.0-gfx906+20261018172427
LLAMA_COMMIT=fd27b2034905f8dadd8bd6d2cc44595f4929d391
PREFIX=${AFTERLIFE_PREFIX:-$HOME/afterlife/gfx906}

if grep -rqs 'repo.radeon.com' /etc/apt/sources.list /etc/apt/sources.list.d/ && [ $LEGACY -eq 0 ]; then
  echo "AMD official ROCm repo configured; remove it first (or use --legacy-6.4.4)." >&2; [ $DRY -eq 1 ] || exit 1; fi

if [ $LEGACY -eq 1 ]; then
  echo "== legacy: official ROCm 6.4.4 + restored Tensile (rocBLAS gfx906 kernels) =="
  echo "Add AMD's 6.4.4 repo (https://repo.radeon.com/rocm/apt/6.4.4 noble main) per AMD docs, install rocm-hip-sdk, then:"
  run curl -fL -o tensile-files-6.4.4.tgz https://github.com/mixa3607/ML-gfx906/releases/download/rocm-tensile-files/tensile-files-6.4.4.tgz
  [ $DRY -eq 1 ] || echo "f8f5d076fd9933809b4179828ee8c961b28a08a693c572fb9c79d78ecefddd13  tensile-files-6.4.4.tgz" | sha256sum -c -
  run sudo tar xf tensile-files-6.4.4.tgz -C /opt/rocm/lib/rocblas/library    # plain tar, not gzip
else
  echo "== TheRock $ROCM_BUILD via mixa3607 apt repo =="
  run sudo install -m 0755 -d /etc/apt/keyrings
  run sudo curl -fsSL https://s3.arkprojects.space/apt-gfx906/ubuntu/gpg -o /etc/apt/keyrings/apt-gfx906.asc
  if [ $DRY -eq 0 ]; then sudo tee /etc/apt/sources.list.d/gfx906.sources >/dev/null <<SRC
Types: deb
URIs: https://s3.arkprojects.space/apt-gfx906/ubuntu
Suites: $(. /etc/os-release && echo "$VERSION_CODENAME")
Components: main
Architectures: amd64
Signed-By: /etc/apt/keyrings/apt-gfx906.asc
SRC
  fi
  run sudo apt-get update
  run sudo apt-get install -y --no-install-recommends "amdrocm7.14=$ROCM_BUILD" "amdrocm-core-sdk7.14=$ROCM_BUILD" "amdrocm7.14-gfx906=$ROCM_BUILD" "amdrocm-core-sdk7.14-gfx906=$ROCM_BUILD"
fi
run sudo usermod -aG video,render "$USER"
export PATH=/opt/rocm/bin:$PATH ROCM_PATH=/opt/rocm
run sudo apt-get install -y git cmake ninja-build build-essential libssl-dev libvulkan-dev glslc mesa-vulkan-drivers vulkan-tools

echo "== llama.cpp b12182: HIP gfx906 + Vulkan baseline =="
run mkdir -p "$PREFIX"
[ -d "$PREFIX/llama.cpp" ] || run git clone https://github.com/ggml-org/llama.cpp.git "$PREFIX/llama.cpp"
run git -C "$PREFIX/llama.cpp" checkout "$LLAMA_COMMIT"
if [ $DRY -eq 1 ]; then echo "+ HIPCXX=\$(hipconfig -l)/clang cmake ... -DGGML_HIP=ON -DGPU_TARGETS=gfx906"; else
  HIPCXX="$(hipconfig -l)/clang" HIP_PATH="$(hipconfig -R)" cmake -S "$PREFIX/llama.cpp" -B "$PREFIX/build-hip" -G Ninja -DGGML_HIP=ON -DGPU_TARGETS=gfx906 -DCMAKE_BUILD_TYPE=Release; fi
run cmake --build "$PREFIX/build-hip" -j"$(nproc)"
run cmake -S "$PREFIX/llama.cpp" -B "$PREFIX/build-vulkan" -G Ninja -DGGML_VULKAN=ON -DCMAKE_BUILD_TYPE=Release
run cmake --build "$PREFIX/build-vulkan" -j"$(nproc)"

if [ $TORCH -eq 1 ]; then
  echo "== optional torch 2.14.1+gfx906 (mixa3607 wheels, py3.12) =="
  ROOT=https://s3.arkprojects.space/py-gfx906/rocm7.14/torch-v2.14.1+gfx906.20261018172427
  run python3.12 -m venv "$PREFIX/venv"
  run curl -fL -o "$PREFIX/idx.txt" "$ROOT/index.txt"
  [ $DRY -eq 1 ] || while read -r f; do curl -fL -o "$PREFIX/$f" "$ROOT/$f"; done < "$PREFIX/idx.txt"
  [ $DRY -eq 1 ] || "$PREFIX/venv/bin/pip" install "$PREFIX"/torch-*.whl "$PREFIX"/torchvision-*.whl
fi
echo "== verify (log out/in for group change) =="
run rocminfo
echo "Run BOTH build-hip and build-vulkan on the same model; Vulkan is the baseline to beat."
