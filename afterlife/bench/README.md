# `afterlife bench` — fixed-methodology benchmark runner

Produces one reproducible result **row** per `(model, quant, backend, card)` and
puts it in a JSON/CSV table. Every row carries a `reproduce_cmd`; the table
builder **refuses to emit a row without one** (SPEC: a cell with no reproduce
command stays out of the table).

## Honest limits first

- **This runner does not run a GPU sweep.** It self-tests on CPU with a **mock
  backend** (fully deterministic, no GPU, no model, no network). Real cards are
  benchmarked by a human GPU step, never by a parallel agent (BUILD_RULES #2).
- **Mock numbers are synthetic.** The throughput the mock prints is plausible,
  deterministic filler to prove the pipeline — it is **not** a measurement of any
  card and must never be quoted as one.
- **Real rows come from the shell adapters** (`llama.cpp`, `vLLM`), which build
  exact commands and parse their output. They raise (never fabricate) if a
  binary is missing. Only the `vLLM` adapter reports the 8-concurrent serving
  aggregate; `llama.cpp` reports `None` for it rather than faking a serving number.

## Commands

```bash
# Prove the whole pipeline end-to-end on CPU (gate must pass):
python -m afterlife.bench selftest

# Print the plan for a real run WITHOUT executing anything:
python -m afterlife.bench run --dry-run \
  --backend llamacpp --model gemma-4-26b-a4b --quant Q4_K_M \
  --gpu-arch sm_70 --model-path /models/gemma.gguf

# Produce a row with the mock backend (deterministic demo):
python -m afterlife.bench run --model demo --quant Q4_K_M --json rows.json --csv rows.csv

# Re-emit stored rows (re-validates + enforces reproduce_cmd):
python -m afterlife.bench table --in rows.json --csv table.csv
```

The top-level `afterlife` dispatcher (owned by the packaging/doctor work) calls
`afterlife.bench.cli:main` with the post-`bench` argv.

## The row

Each row records: `model`, `quant`, `backend` + version, `driver`, `gpu_arch`,
`power_cap_w`, `pp512`+`tg128` at **4k / 16k / 32k** context, the 8-concurrent
serving aggregate (where supported), the **correctness gate** verdict, the
**methodology** (warmup policy, timer, threads, power settings), a
`reproduce_cmd`, and a UTC timestamp.

## The correctness gate

A row passes only when **both** hold (the "fast but broken" guard):

1. **Perplexity** over a fixed text is within **1%** (configurable) of a
   reference row's perplexity (the RTX 3060 control card per SPEC).
2. **A fixed 3-question answer set** scores **3/3**.

The gate is backend-agnostic — it calls only `Adapter.perplexity` and
`Adapter.answer`. A failing gate does not delete the row; the row is emitted and
marked `passed=false`, so failures are visible, not hidden.

## Layout

| File | Role |
|------|------|
| `schema.py` | `Row` + nested records; JSON (canonical) and CSV round-trip |
| `fixtures.py` | fixed gate text, reference ppl, 3-question set, context points |
| `adapter.py` | `Adapter` ABC + `MockAdapter` |
| `adapters_shell.py` | thin `llama.cpp` / `vLLM` adapters (pure parsers + command builders) |
| `gate.py` | perplexity-within-tolerance math + QA scoring |
| `runner.py` | `BenchJob` → `Row`; `plan_job`/`format_plan` for dry-run |
| `table.py` | `TableBuilder` (reproduce_cmd enforcement) |
| `cli.py` | `run` / `selftest` / `table` |
