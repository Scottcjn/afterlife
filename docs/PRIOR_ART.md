# Prior art: community forks that keep stranded GPUs alive

Collected 2026-11-06 by metadata only (GitHub API, READMEs, release pages). Nothing was cloned, built or run, so "works" below means "the upstream README claims it", never "we reproduced it". Raw data: `docs/receipts/`. Afterlife consolidates these projects; it does not compete with them.

Lab-measured numbers (107 tok/s eGPU V100, MI50 Strata figures) are unpublished and are not used here. Every tok/s figure in this file is the upstream author's own claim.

## NVIDIA (sm_70 / sm_61)

### 1Cat-vLLM (sm_70 wheel)
- Repo: https://github.com/1CatAI/1Cat-vLLM (Apache-2.0), 1,475 stars, not archived.
- Latest release: v1.5.2, 2026-11-06 (v1.5.1 2026-10-03). Last commit c98a8d6648, 2026-11-06.
- Serves: Tesla V100 / SM70 only. Upstream numbers are on 4x V100-SXM2 32GB (NVLink, TP4), not a single card.
- Install: wheel `1cat_vllm-1.5.2+cu128-cp312-cp312-linux_x86_64.whl` + `SHA256SUMS` from the release page, or a docker tar. Python 3.12 x86_64 only, PyTorch 2.10.0 + CUDA 12.8 toolkit + compiler/ninja (TileLang JIT). Tested with driver 580.173.02 (README for v1.5.1; recommends 570.124.06+).
- Limits: cp312 only; the wheel has not passed the manylinux gate; needs the CUDA toolkit installed; the README is being renamed 1Cat-LLM so URLs/filenames may change; headline ~260 tok/s is a 4-card demo, not a single-card number; recommended models are NVFP4/DFlash2 checkpoints (Qwen3.8 family), not our three fixed models.
- Status: very active (daily commits).
- Also: renne/1cat-vllm-v100-docker, community daily docker rebuild (Apache-2.0, 12 stars, pushed 2026-07-22; looks stale vs v1.5.x).
- Afterlife reuses: the wheel as the vLLM path for sm_70, pinned and checksummed. Adds: doctor detection, cliff entry, fixed-methodology bench on 1 and 2 cards, perplexity gate.

### sm_70 llama.cpp fork ("Atlas3D or similar")
- NOT FOUND. GitHub searches for "Atlas3D", "volta sm70 llama.cpp", "llama.cpp V100 sm_70 fork" returned no relevant repo (Atlas3D hits are unrelated 3D projects). I could not verify that this fork exists.
- Working assumption: mainline ggml-org/llama.cpp (latest tag b12182, 2026-11-07) still builds for sm_70 / sm_61 with CUDA 12.x (`-DCMAKE_CUDA_ARCHITECTURES=70;61`). Not tested here. af-stacks must confirm with a real build.
- Action for Scott: if you have the Atlas3D link, give it to af-stacks; the cliff DB should not cite it until a URL exists.

### sasha0552/pascal-pkgs-ci (sm_61)
- Repo: https://github.com/sasha0552/pascal-pkgs-ci (MIT), 220 stars, not archived but STALE: last commit 2025-08-23.
- Serves: Pascal (P40, GTX 10xx) via vllm-pascal 0.5.5 to 0.10.0 and triton-pascal 2.2 to 3.4; main nightly "updates daily" per README but no activity after Aug 2025. README says new-GPU support was disabled for v0.7.0+; that path is Pascal-only builds.
- Install: `PIP_EXTRA_INDEX_URL=https://sasha0552.github.io/pascal-pkgs-ci/`, `pip install vllm-pascal==0.10.0` (+ triton-pascal via transient-package), or `ghcr.io/sasha0552/vllm:v0.10.0`. Wheels flagged "soft-broken" from v0.6.5 without a manual torch sed patch.
- Limits: vLLM 0.10.0 is the end of the line (stock is v0.32). Models newer than that vLLM will not load.
- Afterlife reuses: the existence proof and patches as a reference for the sm_61 path (GTX 1060 proxy). Adds: sm_61 llama.cpp as the primary path, honest proxy labelling.

### negativo17 R580 (driver packaging)
- Site: https://negativo17.org/repos/ ; `nvidia-580/` directory dated 2026-09-10, `fedora-nvidia-580.repo` / `epel-nvidia-580.repo` dated 2025-11-19. GitHub mirror (EyeCantCU/nvidia-drivers) is unrelated and stale (Jan 2026).
- Serves: Fedora and RHEL/CentOS only. The lab runs Ubuntu, so negativo17 is not a direct install path. For Ubuntu, use NVIDIA's own 580 packages.
- Facts: NVIDIA states R580 is the last branch for Maxwell/Pascal/Volta (Phoronix report; official NVIDIA page not fetched). Version number of the newest 580.x in negativo17 NOT determined.
- Licence: NVIDIA proprietary driver; negativo17 repackages. Treat as not redistributable by us.
- Afterlife reuses: nothing directly; cited for the R580 cliff and as a fallback on RPM distros.

## AMD (gfx906)

### mixa3607/ML-gfx906
- Repo: https://github.com/mixa3607/ML-gfx906 (MIT), 376 stars, active (pushed 2026-11-06; release 20261031203345 on 2026-10-31).
- Serves: gfx906 (MI50 / MI60 / Radeon VII / Pro VII). Subprojects: ROCm (TheRock build), llama.cpp (+multiruntime), vLLM, PyTorch, ComfyUI, Strata, Maya, rocm-tensile, amd-memory-tweak, tuning tools.
- Install: apt repo (Ubuntu 24.04) `amdrocm10.1-gfx906` etc. from s3.arkprojects.space/apt-gfx906; or docker `mixa3607/rocm-gfx906:{7.14,10.0,10.1}-complete` (build 20261018172427); `mixa3607/llama.cpp-gfx906:<ver>-rocm-10.1` (daily); `mixa3607/vllm-gfx906:0.20.1-rocm-{6.3.3,7.2.1}-aiinfos`.
- Limits: do not mix with official AMD repos; gfx906 has no hipBLASLt device library (INT8 `torch._int_mm` issue, see their HIPBLASLT-GFX906.md); legacy 6.3.3/6.4.4/7.x builds are unsupported from release 20260802001858; Ubuntu 24.04 only; vLLM is 0.20.1, far behind v0.32; hosting is a personal S3 bucket (single point of failure).
- Status: maintained.
- Afterlife reuses: images/apt as the gfx906 base, pinned by digest. Adds: doctor, bench, cliff matrix, Vulkan comparison column. Credit mixa3607 prominently.

### ROCm/TheRock (gfx906 nightlies)
- Repo: https://github.com/ROCm/TheRock (MIT), 1,430 stars, very active (pushed 2026-11-07).
- Releases (tags): therock-7.12 2026-03-26, 7.13 2026-05-15, 7.14 2026-07-15, 7.14.1 2026-08-31, 10.0 2026-08-26, 10.1 2026-10-05.
- gfx906: listed in RELEASES.md as `device-gfx906` (Instinct MI60/MI50, Radeon Pro VII, Radeon VII). Install via pip index https://nightly.repo.amd.com/rocm/whl-next/ (nightly) or tarballs. Whether the official gfx906 nightly is tested or only built is NOT verified; mixa3607 rebuilds it for gfx906 themselves, which suggests the official artifacts are not sufficient.
- Limits: nightlies "may be unstable"; layout changed at 10.1.
- Spec drift: SPEC.md pins "TheRock 7.12 nightly". 7.12 is now 7 months old; mixa3607 ships 7.14 / 10.0 / 10.1. See pins below.
- Afterlife reuses: via mixa3607 packaging. Adds: pin + regression test.

### nullkalahar/mi50-rocm7
- Repo: https://github.com/nullkalahar/mi50-rocm7, 11 stars, NO LICENSE file (all rights reserved by default: do not copy its scripts into Afterlife; link and cite only). Last commit 2026-10-04.
- A documentation guide: ROCm 7.0.2 local install + "tensor injection" (restoring Tensile files), TheRock 7.14+ apt method, llama.cpp SOLVE_TRI fix for Qwen3/3.5, LLVM max-ilp flag, NO_VMM=1, power cap 150-180 W, VBIOS-parity warning for multi-GPU.
- Status: maintained as docs, small. Afterlife reuses: the facts (cited) as a checklist for the cliff DB; writes its own text.

### llama.cpp gfx906 forks
- sixvolts/llamacpp-gfx906-furnace (MIT, 23 stars): branch gfx906-perf, active (2026-11-07). "Optimized build of llama.cpp for gfx906/Vega20."
- milpster/gfx906-llama-cpp (MIT, 31 stars): last commit 2026-09-29 (gfx906 packed-byte subtraction, tracks upstream PR #29478).
- xxDoman/llama-mi50-rocm7.2 (NO LICENSE, 0 stars): llama.cpp b12128, docker `xxdoman/llama-mi50-rocm7.2:v5`, pushed 2026-11-06. Do not redistribute.
- THEman6989/llama.cpp-gfx906-wrapper (no licence). taobaoww2010-alt (no licence).
- Not verified: which one is the "llama.cpp-gfx906 fork" you meant; the first two carry real patches. Perf claims in their READMEs were not checked.
- Afterlife reuses: mixa3607's llama.cpp images as default, optionally the furnace branch as a tested alternative. Adds: Vulkan fallback and bench rows.

### vLLM for gfx906
- nlzy/vllm-gfx906: ARCHIVED (true) on 2026-02-20 ("gfx906/main", last commit "[gfx906] end"); 436 stars, Apache-2.0. Pinned to ROCm 6.3, torch 2.9, triton-gfx906 3.5.0. Docker `nalanzeyu/vllm-gfx906`. MoE quantised models "significantly slow". Author invites forks.
- Live successors: ttdxq/gfx906-vllm (Apache-2.0, 50 stars, pushed 2026-10-28, rccl-gfx906 2.27.7 for ROCm 7.2.4); ai-infos/vllm-gfx906-mobydick (Apache-2.0, 94 stars, pushed 2026-10-08; used by mixa3607 images); nick413-bit/gfx906-fa-vllm (Apache-2.0, 17 stars, stale Apr 2026); 0c33/mi50-vllm-lab (Apache-2.0, 8 stars).
- Afterlife reuses: mixa3607's vllm-gfx906 (0.20.1) as the pinned vLLM fork; credit nlzy as origin. Adds: serving 8-concurrent number plus correctness gate.

## Licences that forbid or complicate redistribution
- NVIDIA driver, CUDA toolkit, cuDNN: proprietary NVIDIA EULAs. Do not bundle in a published container. Redistribution is only allowed for the specific files listed in the CUDA EULA's redistributable attachment, and I did not verify that list against our containers. Default: ship build-from-recipe (Dockerfile that pulls from NVIDIA's apt repo at build time).
- 1Cat-vLLM wheel itself is Apache-2.0 but depends on the CUDA toolkit installed separately (they do not bundle it). The release docker tar was not inspected; do not re-host it until its layers are checked for CUDA libraries.
- ROCm / TheRock: mostly MIT/permissive components. Per-package licences not audited. mixa3607 images contain a mix; re-hosting is a question for after an audit, so reference by digest rather than copying.
- No licence at all (default all-rights-reserved): nullkalahar/mi50-rocm7, xxDoman/llama-mi50-rocm7.2 and ollama-mi50-*, THEman6989 wrapper. Cite and link only.
- Model weights: each keeps its own licence per lab rule 0; nothing here is a model.

## Version and date pins for af-stacks (as of 2026-11-06)
NVIDIA legacy:
- Driver: 580 branch (last for Volta/Pascal). Exact 580.x: 580.173.02 is the one 1Cat tested; confirm the newest 580.x on Ubuntu before pinning.
- CUDA: SPEC says 12.9; 1Cat-vLLM wheel is built for CUDA 12.8 + torch 2.10.0 + Python 3.12. Conflict: the vLLM path needs a separate venv/container on cu128/torch 2.10, distinct from the spec's torch 2.14.0 cu126 llama.cpp/torch stack.
- Stock reference points (for the cliff matrix): torch 2.15.0 (2026-10-28), vLLM v0.32.0 (2026-10-18), llama.cpp b12182 (2026-11-07), Ollama v0.40.15 (2026-11-03). Whether torch 2.14/2.15 actually drop sm_70/61 wheels was not verified by me: SPEC asserts it; verify with a real `pip install` on the proxy machine and record the error string.
- vLLM: 1Cat-vLLM v1.5.2 (2026-11-06) wheel; SHA256 from the release's SHA256SUMS (not yet fetched/recorded).
- sm_61: pascal-pkgs-ci vllm-pascal==0.10.0 is the last (2025-08).
AMD gfx906:
- ROCm: ML-gfx906 TheRock builds 7.14.0 / 10.0.0 / 10.1.0, build 20261018172427 (Ubuntu 24.04). SPEC's "TheRock 7.12 nightly" is outdated: recommend pinning 7.14.0-gfx906+20261018172427 (the oldest TheRock build mixa3607 still ships, nearest the spec) and testing 10.1 as a candidate.
- Fallback: ROCm 6.4.4 / 6.3.3 images exist but are unsupported by mixa3607 since 20260802001858.
- llama.cpp: mixa3607 `llama.cpp-gfx906:<ver>-rocm-10.1`; pin by digest.
- vLLM: mixa3607 `vllm-gfx906:0.20.1-rocm-7.2.1-aiinfos` (ROCm 7.2.1, not a TheRock build; a mismatch with the 7.14 base to resolve).
- Ollama: SPEC says 0.13 dropped gfx906; not verified here (no release note mentions gfx906 in my search of release bodies).

## Summary table
| Project | Card | Maintained | Licence | Reuse / add |
|---|---|---|---|---|
| 1Cat-vLLM | sm_70 | yes | Apache-2.0 | wheel / doctor+bench |
| sm_70 llama.cpp fork | sm_70 | not found | - | mainline build |
| pascal-pkgs-ci | sm_61 | stale 2025-08 | MIT | reference / llama.cpp path |
| negativo17 R580 | sm_70/61 | yes (RPM only) | proprietary | cite only |
| ML-gfx906 | gfx906 | yes | MIT | base images / tests |
| TheRock | gfx906 | yes | MIT | via mixa3607 |
| mi50-rocm7 | gfx906 | docs | none | cite only |
| gfx906 llama.cpp forks | gfx906 | furnace yes | MIT (2 of 5) | optional alt |
| nlzy vllm-gfx906 | gfx906 | ARCHIVED | Apache-2.0 | origin credit |

## What I could not verify
No builds or installs; no wheel SHA256; stars/dates are from the API at collection time; Atlas3D fork; torch 2.15 / Ollama 0.13 cliff claims; per-component licences inside docker images; the official TheRock gfx906 test status.
