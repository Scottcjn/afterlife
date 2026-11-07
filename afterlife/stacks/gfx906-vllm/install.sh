#!/usr/bin/env bash
# Afterlife gfx906-vllm: build upstream image locally from source. UNTESTED, 2026-11-06. Needs docker, ~100GB disk, many cores.
set -euo pipefail
DRY=0; [ "${1:-}" = "--dry-run" ] && DRY=1
run() { echo "+ $*"; [ $DRY -eq 1 ] || "$@"; }
PREFIX=${AFTERLIFE_PREFIX:-$HOME/afterlife/gfx906-vllm}
REF=${VLLM_REF:-main}   # head at survey: e7b96a5ee3799a6f9286834bbc911375a75db64b -- set VLLM_REF to a sha to pin
run mkdir -p "$PREFIX"
[ -d "$PREFIX/src" ] || run git clone https://github.com/ai-infos/vllm-gfx906-mobydick.git "$PREFIX/src"
run git -C "$PREFIX/src" checkout "$REF"
[ $DRY -eq 1 ] || { cd "$PREFIX/src"; MAX_JOBS="${MAX_JOBS:-16}" bash build_and_push_docker.sh; }
echo "Built tag: aiinfos/vllm-gfx906-mobydick:v0.30.0.x-rocm7.14-pytorch2.13.0 (local only; do not --push)"
