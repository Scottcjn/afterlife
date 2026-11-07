# af-doctor REPORT (2026-11-06)

Scope: `afterlife doctor` + the cliff database. Files I own:
`afterlife/cliff_db.yaml`, `afterlife/cliff_db.json` (generated mirror),
`afterlife/{cli,cliffs,detect,doctor}.py`, `tests/{__init__,fixtures,test_doctor}.py`.
No push. No GPU sweeps. No lab SSH. No RustChain nodes touched.

## What I built
- **`afterlife/cliff_db.yaml`** — 8 support-cutoff entries. Each carries a
  SOURCE url, `confidence` (confirmed/partial/unverified) and a
  `source_confirmed` bool, plus `cliff_version` / `last_good_version` / exact
  `fix`. A `stock_latest` block (torch 2.15.0, vLLM 0.32.0, Ollama 0.40.15,
  ROCm 7.2.0, flash_attn 2.8.0) drives "what if you install latest?" verdicts.
- **`cliff_db.json`** — byte-for-content mirror of the YAML so `doctor` runs
  stdlib-only (package has zero runtime deps per af-pkg's pyproject; PyYAML is
  the optional `yaml` extra). A test asserts the two never drift.
- **`detect.py`** — pure parsers for `nvidia-smi` (CSV, incl. `[Not Supported]`
  compute_cap → name-map fallback), `rocminfo` (gfx agents), `lspci` (fallback),
  `nvcc`, plus framework probes (torch/vllm/flash_attn via import; ollama/
  llama.cpp via `--version`). Every probe is wrapped; a missing tool → `None`,
  nothing raises.
- **`cliffs.py`** — loader + dependency-free version comparison + per-GPU
  verdicts (BROKEN / AT_RISK / SAFE / INFO / UNKNOWN).
- **`doctor.py` / `cli.py`** — `afterlife doctor [--json]`; human report lists
  per-GPU arch, what breaks (exact), the pinned fix, confidence + source;
  exit code 1 if any GPU is BROKEN (CI-usable).

## Cliff entries — source-confirmed vs not
| id | claim | confidence | source_confirmed |
|----|-------|-----------|------------------|
| cuda13_drops_pre_turing | CUDA 13.0 drops offline-compile/library for sm_50–72 | confirmed | yes |
| r580_last_driver_branch | R580 last branch for pre-CC-7.5 (thru mid-2028) | confirmed | yes |
| torch215_drops_pre_turing_wheels | torch **2.14 last cu126 wheel**; 2.15 drops sm_50/60/70 | confirmed | yes |
| rocm7_drops_gfx906 | ROCm 7.x lists gfx906/gfx900 unsupported | confirmed | yes |
| flashattn2_needs_sm80 | FA2 needs sm_80+; Volta/Pascal have no kernels | confirmed | yes |
| vllm_dropped_v100_sm70 | vLLM dropped V100 (V0 removal, v0.10 Jul 2025) | **partial** | no |
| rocm64_drops_gfx906_tensile | ROCm 6.4 stopped shipping gfx906 Tensile kernels | **unverified** | no |
| ollama013_dropped_gfx906 | Ollama 0.13.0 dropped gfx906 | **unverified** | no |

### What I could NOT verify (flagged in-DB, never asserted as fact)
- **vLLM / V100 (partial):** issue #18571 lists "V100 support" under "Features
  Permanently Dropped" and dates v0.10.0 to 2025-07-01, but it does NOT name
  sm_70 nor tie the drop to a version; maintainers later said V1 "should be
  supported already." Treated as a deprecation direction, not a hard cutoff.
- **ROCm 6.4 Tensile (unverified):** no AMD primary doc confirms gfx906 Tensile
  logic-file removal at 6.4; only third-party leads (mixa3607). gfx906
  maintenance-mode since ROCm 6.0 / last full support 5.7 IS documented.
- **Ollama 0.13.0 (unverified):** v0.13.0 release notes mention only "Improved
  VRAM information detection for AMD GPUs" — NO gfx906 drop. The 0.13.0 drop
  point is unconfirmed and may be inaccurate; fix (OLLAMA_VULKAN=1 / pin ≤0.12 /
  fork) still holds regardless.

## Test results
`ruff check` clean, `mypy --strict` clean (7 source files), **14/14** doctor
tests pass; full repo suite **65 passed** (my 14 + siblings' 51). Fixtures cover
V100 sm_70 (new driver = BROKEN everywhere; R580 = AT_RISK not BROKEN), GTX 1060
sm_61, MI50 gfx906, RTX 3060 sm_86 (control, SAFE), every tool absent (no crash),
and an unrecognised GPU (arch=None → UNKNOWN, fail-safe, no guessed cliffs).

## Needs Scott / coordinator
- **Packaging gap (coordinator):** af-pkg's `pyproject.toml` package-data is
  `afterlife = ["data/*","data/**/*"]`; my `cliff_db.{yaml,json}` sit at the
  package root, so a non-editable `pip install` would NOT bundle them. Either
  add `afterlife = ["*.yaml","*.json"]` to package-data or move the DB into
  `afterlife/data/`. Works today for source / `pip install -e` runs.
- **Regenerate JSON on YAML edits:** `cliff_db.json` is generated; the sync test
  guards drift. If you edit the YAML, regenerate:
  `python -c "import importlib,json; d=importlib.import_module('yaml').safe_load(open('afterlife/cliff_db.yaml')); json.dump(d,open('afterlife/cliff_db.json','w'),indent=2)"`
- **Verify the 3 unconfirmed claims** against vendor notes before any public
  README states them as fact (ROCm 6.4 Tensile, Ollama 0.13 gfx906, exact vLLM
  sm_70 cutoff). They are flagged unverified/partial in the DB today.

Queue ids added: none (no publish/launch step reached).
