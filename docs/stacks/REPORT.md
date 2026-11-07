# af-stacks REPORT (2026-11-06)

Scope: `afterlife/stacks/` + `docs/stacks/`. Recipes only. Nothing was built, downloaded (except one 134 MB Tensile tar for hashing), or run on a GPU. No push.

## What exists
- `afterlife/stacks/index.yaml` — arch -> recommended stack map for `afterlife doctor` (keys `sm_70`, `sm_61`, `gfx906`, `sm_86`; fields `recommended`, `alternatives`, `support`, `baseline`, `cliff`).
- Five stacks, each with `stack.yaml`, `Dockerfile`, `install.sh` (`--dry-run` supported): `nvidia-legacy`, `nvidia-legacy-vllm-1cat`, `gfx906`, `gfx906-vllm`, `control-sm86`.
- `afterlife/stacks/validate.py` — loads every YAML, checks index references and exec bits.

## Verification run
- `python3 -I validate.py` -> OK (6 YAML files parse; all index refs resolve).
- `bash -n` on 5 install scripts OK; `--dry-run` of all 5 exits 0; shellcheck: only SC1091 info (os-release).
- ruff check/format and mypy clean on validate.py. Dockerfiles NOT linted/built (no hadolint, no builds).

## Deviations from the SPEC (per coordinator + findings)
1. vLLM split into its own stacks (1Cat needs CUDA 12.8 / torch 2.10 / py3.12 vs. CUDA 12.9 / torch 2.14 cu126).
2. TheRock 7.12 is stale: pinned 7.14.0-gfx906+20261018172427; 10.1 = test target. ROCm 6.4.4 + Tensile = legacy fallback.
3. No "Atlas3D" llama.cpp fork: mainline b12182 (commit fd27b20...), "expected to build, untested".
4. vLLM gfx906: ai-infos/vllm-gfx906-mobydick (Apache-2.0) primary, ttdxq alternative; nlzy archived (credited). Newest ai-infos image is ROCm 7.14/torch 2.13.0; mixa3607's older vLLM image is on ROCm 7.2.1 (kept separate).
5. Control row uses torch 2.15.0 from PyPI (cu13) + CUDA 13.4.3, driver 595.80.

## Pins and confirmation
"Confirmed" = URL/metadata fetched 2026-11-06. It does NOT mean built or working.

| Pin | Value | Confirmed |
|---|---|---|
| NVIDIA driver R580 | 580.196.07 .run | URL 200; sha not recorded |
| CUDA toolkit | 12.9.1 (.run URL; apt cuda-toolkit-12-9 present in ubuntu2404 repo) | yes |
| nvidia/cuda 12.9.1-devel-ubuntu24.04 | sha256:020bc241... | yes (Docker Hub API) |
| torch | 2.14.0+cu126 cp312 wheel, 869 MB; torchvision 0.29.0 (requires torch==2.14.0) | wheel+metadata yes; **sm_70/61 kernels inside NOT verified** |
| llama.cpp | b12182 = fd27b2034905f8dadd8bd6d2cc44595f4929d391; `-DCMAKE_CUDA_ARCHITECTURES="70;61"` | tag yes; build no. (Also exists: v0.9.0 = cd959bae...) |
| 1Cat-vLLM | v1.5.2 wheel cu128/cp312, sha256 a27afc51..., tag commit 2bb8c2b9 | yes; torch 2.10.0 from README, not from wheel metadata |
| nvidia/cuda 12.8.1-devel-ubuntu24.04 | sha256:520292db... | yes |
| TheRock gfx906 | 7.14.0-gfx906+20261018172427 via mixa3607 apt (package + version + sha256 read from Packages index) | yes; install not run |
| Tensile 6.4.4 | tar sha256 f8f5d076... (downloaded, hashed; it is plain tar, 156 gfx906 files) | yes |
| ROCm 6.4.4 official apt | repo.radeon.com/rocm/apt/6.4.4 noble | InRelease read |
| mixa torch gfx906 | 2.14.1+gfx906.20261018172427 wheels (index.txt read) | yes; not downloaded |
| gfx906 llama.cpp forks | sixvolts/llamacpp-gfx906-furnace (MIT, HEAD 17be77b), milpster/gfx906-llama-cpp (MIT, HEAD 1373e88) | repo+license yes; HEADs only, no commit pinned |
| ai-infos vLLM image | v0.30.0.x-rocm7.14-pytorch2.13.0-260726fedb27, digest sha256:b7f62e58... | yes; **source commit for that tag not identified** (main HEAD e7b96a5 recorded as seen) |
| ttdxq/gfx906-vllm | Apache-2.0, HEAD 80f14ac | repo yes; not evaluated |
| Control | driver 595.80, CUDA 13.4.3 image sha256:5626a7d0..., torch 2.15.0 (PyPI) | yes; CUDA minor inside torch wheel unknown |
| Ubuntu 24.04 | sha256:fe815609... | yes |

## Redistribution
- NVIDIA driver/CUDA toolkit/cuDNN: proprietary. CUDA EULA allows redistribution only of Attachment A runtime files, unmodified, inside an application (excerpts read, not legal advice). So: recipes only, never push images containing nvcc/toolkit; driver is host-side. 1Cat's docker tarball is cited, not re-hosted (it bundles a CUDA 12.8 compiler).
- ROCm/TheRock: mostly permissive OSS but **I did not read the AMD license page in full** — marked unreviewed. The gfx906 apt packages are mixa3607's third-party rebuild; trust and hosting are theirs.
- mi50-rocm7 and xxDoman builds: no license, cited only.
- No model weights were downloaded, so no LICENSE_RECEIPT.txt was created.

## Not verified / needs Scott
- Nothing builds yet; all Dockerfiles/scripts are unrun. First real test = bench plan on a V100, MI50 (HIP vs Vulkan), 3060.
- torch 2.14 sm_70/61 support; torch 2.15 dropping them (SPEC claim, untested); Ollama 0.13/gfx906 claim; llama.cpp on sm_61 w/ CUDA 12.9.
- sm_61 is a GTX 1060 proxy for P40.
- 1Cat speed numbers are 4x V100-SXM2 TP4; single-card behavior unknown. Lab "~107 tok/s" and MI50 Strata figures remain unpublished lab measurements; none appear in these files.
- Whether hipcc is included in `amdrocm-core-sdk7.14-gfx906` is inferred from mixa's Dockerfile.
- Queue ids added: none (nothing to publish).
