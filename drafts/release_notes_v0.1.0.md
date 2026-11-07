# afterlife v0.1.0

**Your datacenter GPU got dropped by CUDA/ROCm. It still works — if you pin the
right stack.** afterlife tells you exactly what will break on a vendor-dropped
card (V100, Pascal, MI50 and friends) and the pinned versions that keep it
running, then gives you a reproducible benchmark harness to prove it.

First public cut (v0.1, alpha). Honest about what's measured and what isn't.

## What works today
- **`afterlife doctor`** — detects your GPUs, driver, CUDA/ROCm toolkit and
  frameworks, then reports, per card: what's about to break, why, and the exact
  fix (e.g. "CUDA 13 drops sm_70 → pin 12.9"; "PyTorch 2.15 drops cu126 wheels →
  stay on 2.14"). Exit code is CI-usable. JSON output with `--json`.
- **Cliff database** — the version cliffs that strand each architecture, each
  entry carrying a confidence level and whether its source is confirmed.
  Entries we could not confirm against vendor notes are marked UNVERIFIED rather
  than asserted.
- **Pinned stack recipes** — build-from-recipe manifests for nvidia-legacy,
  1Cat vLLM, gfx906 (+vLLM), and an sm86 control.
- **`afterlife bench`** — a fixed-methodology benchmark harness (pp/tg at set
  context, serving concurrency, a correctness gate: perplexity within 1% of a
  reference + a small QA set). Backend-agnostic adapters.

## Honest limits (read first)
- **No measured performance numbers ship in v0.1.** Every tok/s cell in the
  cliff matrix is `TODO (pending bench)`. The harness is here; the fleet run
  that fills it is not done (`eval/BENCH_FLEET_PLAN.md`). Any lab figure you may
  have seen (e.g. ~107 tok/s on a V100 eGPU) is a single unverified lab
  measurement and is labelled as such — do not cite it as a benchmark.
- Cliff entries are claims until source-confirmed; the DB says which are which.
- This is guidance + tooling, not a driver or a fork. It tells you the pins;
  you run them.

## Install / run
```bash
pip install afterlife-gpu
afterlife doctor            # what will break on this box, and the fix
afterlife doctor --json     # machine-readable
afterlife bench selftest    # prove the bench pipeline end-to-end
```

## Not included / not implied
No token, no coin. afterlife is diagnostics + recipes + a benchmark harness.

---
License: Apache-2.0. Credits: 1Cat-vLLM, mixa3607, nlzy, TheRock, llama.cpp.
