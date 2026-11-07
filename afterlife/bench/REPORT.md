# REPORT — `afterlife bench` (agent: af-bench)

## What I built

A fixed-methodology benchmark runner under `afterlife/bench/` (tests under
`tests/bench/`). It is CPU-self-testing: it runs end-to-end against a
deterministic mock backend with no GPU, no model download, and no network. No
GPU sweep, no SSH to lab machines, no RustChain nodes touched (BUILD_RULES #2).

Modules:
- `schema.py` — `Row` + nested EnvInfo/PerfPoint/Methodology/CorrectnessResult;
  JSON (canonical) and CSV (fixed columns) that round-trip losslessly.
- `fixtures.py` — fixed original licence-free gate text; reference perplexity;
  fixed 3-question answer set; 4k/16k/32k context points.
- `adapter.py` — backend-agnostic `Adapter` ABC + complete `MockAdapter`
  (configurable perplexity + answer correctness to drive both gate paths).
- `adapters_shell.py` — thin llama.cpp / vLLM adapters: pure command builders +
  output parsers (`parse_perplexity`, `parse_llama_bench_tps`). Raise
  `AdapterError` (never fabricate) if a binary is missing. Only vLLM reports the
  8-concurrent serving aggregate; llama.cpp returns None rather than faking it.
- `gate.py` — correctness gate: perplexity within 1% (configurable) of a
  reference AND 3/3 on the fixed questions. Backend-agnostic.
- `runner.py` — `BenchJob` → `Row`; `plan_job`/`format_plan` serve `--dry-run`
  from static metadata + the pure `reproduce_cmd` (executes nothing).
- `table.py` — `TableBuilder` that re-validates rows and refuses any row without
  a `reproduce_cmd`.
- `cli.py` / `__main__.py` — `run` (with `--dry-run`), `selftest`, `table`.

## Requirements coverage
1. Row (JSON+CSV): model, quant, backend+version, driver, gpu_arch, power cap,
   pp512+tg128 at 4k/16k/32k, 8-concurrent serving where supported, gate result,
   methodology — done.
2. Gate: perplexity within 1% of reference + 3/3 QA, backend-agnostic, shell-out
   llama.cpp/vLLM adapters + mock for tests — done.
3. Every row carries `reproduce_cmd`; table refuses rows without one — done.
4. `run --dry-run` prints plan and executes nothing; `selftest` proves pipeline
   end-to-end on mock (gate passes) — done.
5. Methodology (warmup, timer, threads, power) recorded per row — done.

## Test results
`51 passed` (schema/round-trip, adapters + parsers, gate pass/fail/partial,
perplexity-within-1% math, runner, dry-run no-execution guarantee, table
enforcement, CLI run/dry-run/selftest/table).

Tooling (workspace venv ../.venv-bench, Python 3.13):
- `ruff check afterlife/bench tests/bench` → All checks passed
- `mypy afterlife/bench tests/bench` → Success: no issues found in 17 source files
  (repo pyproject.toml sets strict = true)

## Queue ids added
None. This runner publishes/launches nothing (BUILD_RULES #1), so no
growth-week1/QUEUE.jsonl entry was warranted.

## What needs Scott
- Real cliff-matrix rows are a human GPU step: point the llama.cpp/vLLM adapters
  at actual binaries + model and run per card. The runner prints the exact
  `reproduce_cmd`; `--dry-run` shows the plan first.
- Top-level `afterlife` dispatcher (`afterlife.cli:main`, declared in the shared
  pyproject.toml by the packaging work) still needs to route `afterlife bench …`
  into `afterlife.bench.cli:main`. That `afterlife/cli.py` is shared scaffolding
  owned outside the bench lane; left for integration.

## What I could NOT verify
- Shell adapters were exercised only with injected fake runners + their pure
  parsers. Parsing real llama-bench/llama-perplexity/vLLM output was NOT run
  against live binaries (no GPU per the rules); exact output-format assumptions
  are unconfirmed against current upstream.
- All mock throughput numbers are synthetic; nothing here measures a real card.
