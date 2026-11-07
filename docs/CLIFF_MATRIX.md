# Cliff Matrix — template v0.1

**Every cell in this file is a slot. No cell holds a number until its
`reproduce:` command has been run and the `afterlife bench` JSON row is
checked in under `bench/rows/`.** The bench plan (Scott's, run on lab
hardware, not by agents) fills the slots in. Until then the matrix is a
contract, not a result.

Conventions used throughout:

- `TODO (pending bench)` — no measurement exists.
- `n/a (VRAM)` — the model does not fit the card at the pinned quant; this
  is a stated result, not a missing one.
- `reproduce:` — the exact command that produced (or will produce) the
  cell. Empty slot = `TODO`. A cell without one is not allowed in
  [README.md](../README.md).
- `row:` — path to the checked-in JSON row, e.g.
  `bench/rows/<card>/<model>/<date>.json`.
- `lab-only` — a single, unpublished workshop observation. Flagged in
  the cell, never used as the cell's value.

Correctness gate (applies to every Afterlife cell): perplexity on the fixed
text within **1 %** of the RTX 3060 reference **and** **3/3** on the fixed
answer set. A failing row keeps its tok/s but is struck through.

---

## Reference models

| Id | Class | Candidate | Quant (pinned) | License + receipt |
|---|---|---|---|---|
| M1 | dense ~8B | TODO (bench plan pins id + revision sha) | TODO | `models/M1/LICENSE*`, `models/M1/LICENSE_RECEIPT.txt` |
| M2 | ~27B dense **or** 26B MoE | **Gemma 4 26B A4B — a 4B-active MoE** (alternate: a ~27B dense, if swapped) | TODO | `models/M2/LICENSE*`, `models/M2/LICENSE_RECEIPT.txt` |
| M3 | 30B-class MoE, partial CPU offload | TODO | TODO | `models/M3/LICENSE*`, `models/M3/LICENSE_RECEIPT.txt` |

Fixed perplexity text: `bench/fixtures/ppl_text.txt` (TODO: commit).
Fixed answer set (3 items): `bench/fixtures/answers.jsonl` (TODO: commit).
Fixed 8-concurrent serving prompt set: `bench/fixtures/serve_prompts.jsonl`
(TODO: commit).

---

## Cards (rows)

| Row | Card | Arch | Legend | Bus / notes |
|---|---|---|---|---|
| R1 | Tesla V100 PCIe 16 GB | sm_70 | supported | PCIe x16, C4130 host |
| R2 | Tesla V100 SXM2 32 GB | sm_70 | supported, **eGPU x4** | M.2 → SXM2 adapter, PCIe Gen3 x4, 200 W / 1290 MHz cap |
| R3 | GTX 1060 6 GB | sm_61 | **proxy** for P40 / Pascal | 6 GB; many M2/M3 cells are `n/a (VRAM)` |
| R4 | Radeon Instinct MI50 | gfx906 | supported, **16 GB board** | Radeon Pro VII 16 GB vBIOS; PSP rejects 32 GB images |
| R5 | RTX 3060 12 GB | sm_86 | **control** | vendor-supported; correctness reference |
| R6 | Tesla P40 24 GB | sm_61 | **untested** | not owned; row exists so the slot exists |
| R7 | Turing (T4 / RTX 20xx) | sm_75 | **untested**, v0.2 | next on the cut list |

---

## Column A — Stock-latest result

For each framework at its **latest release on the bench date**: `runs`,
`runs slow (N tok/s)`, or the **exact error string**. Record version +
date in the row.

| Row | Ollama latest | vLLM latest | PyTorch latest (`pip install torch`) | Official ROCm latest |
|---|---|---|---|---|
| R1 V100 PCIe | TODO (pending bench)<br>`reproduce:` TODO<br>`row:` TODO | TODO (pending bench)<br>`reproduce:` TODO<br>`row:` TODO | TODO (pending bench)<br>`reproduce:` TODO<br>`row:` TODO | n/a (NVIDIA) |
| R2 V100 SXM2 eGPU x4 | TODO (pending bench)<br>`reproduce:` TODO<br>`row:` TODO | TODO (pending bench)<br>`reproduce:` TODO<br>`row:` TODO | TODO (pending bench)<br>`reproduce:` TODO<br>`row:` TODO | n/a (NVIDIA) |
| R3 GTX 1060 (proxy) | TODO (pending bench)<br>`reproduce:` TODO<br>`row:` TODO | TODO (pending bench)<br>`reproduce:` TODO<br>`row:` TODO | TODO (pending bench)<br>`reproduce:` TODO<br>`row:` TODO | n/a (NVIDIA) |
| R4 MI50 16 GB | TODO (pending bench)<br>`reproduce:` TODO<br>`row:` TODO | TODO (pending bench)<br>`reproduce:` TODO<br>`row:` TODO | TODO (pending bench)<br>`reproduce:` TODO<br>`row:` TODO | TODO (pending bench)<br>`reproduce:` TODO<br>`row:` TODO |
| R5 RTX 3060 (control) | TODO (pending bench)<br>`reproduce:` TODO<br>`row:` TODO | TODO (pending bench)<br>`reproduce:` TODO<br>`row:` TODO | TODO (pending bench)<br>`reproduce:` TODO<br>`row:` TODO | n/a (NVIDIA) |
| R6 P40 (untested) | — | — | — | n/a |
| R7 Turing (untested) | — | — | — | n/a |

Expected cliff-database entries these cells should *confirm or refute*
(these are database claims, not measurements): CUDA 13 drops sm_50–70;
R580 is the last driver branch for Volta/Pascal; torch 2.15 ships no
sm_70/sm_61 wheels; latest vLLM refuses sm_70; ROCm 7 lists gfx906 as
unsupported; Ollama 0.13 dropped gfx906.

---

## Column B — Afterlife pp512 / tg128 (three models, three contexts)

Each cell: `pp512 / tg128` tok/s at **4k | 16k | 32k** context, median of 3
warm runs. One sub-table per model.

### B.1 — M1 (dense ~8B)

| Row | 4k pp512 / tg128 | 16k pp512 / tg128 | 32k pp512 / tg128 | reproduce / row |
|---|---|---|---|---|
| R1 V100 PCIe | TODO (pending bench) | TODO (pending bench) | TODO (pending bench) | `reproduce:` TODO<br>`row:` TODO |
| R2 V100 SXM2 eGPU x4 | TODO (pending bench) | TODO (pending bench) | TODO (pending bench) | `reproduce:` TODO<br>`row:` TODO |
| R3 GTX 1060 (proxy) | TODO (pending bench) | TODO (pending bench) | TODO (pending bench) | `reproduce:` TODO<br>`row:` TODO |
| R4 MI50 16 GB | TODO (pending bench) | TODO (pending bench) | TODO (pending bench) | `reproduce:` TODO<br>`row:` TODO |
| R5 RTX 3060 (control) | TODO (pending bench) | TODO (pending bench) | TODO (pending bench) | `reproduce:` TODO<br>`row:` TODO |
| R6 P40 (untested) | — | — | — | — |
| R7 Turing (untested) | — | — | — | — |

### B.2 — M2 (Gemma 4 26B A4B, **4B-active MoE**; or ~27B dense alternate)

| Row | 4k pp512 / tg128 | 16k pp512 / tg128 | 32k pp512 / tg128 | reproduce / row |
|---|---|---|---|---|
| R1 V100 PCIe | TODO (pending bench) | TODO (pending bench) | TODO (pending bench) | `reproduce:` TODO<br>`row:` TODO |
| R2 V100 SXM2 eGPU x4 | TODO (pending bench)<br>*lab-only: ~107 tok/s tg observed once on `llama-server`, 200 W / 1290 MHz, not under this methodology, no row — NOT a value* | TODO (pending bench) | TODO (pending bench) | `reproduce:` TODO<br>`row:` TODO |
| R3 GTX 1060 (proxy) | n/a (VRAM) unless the pinned quant fits 6 GB — bench plan decides | n/a (VRAM) | n/a (VRAM) | `reproduce:` TODO (fit check) |
| R4 MI50 16 GB | TODO (pending bench) | TODO (pending bench) | TODO (pending bench) | `reproduce:` TODO<br>`row:` TODO |
| R5 RTX 3060 (control) | TODO (pending bench) | TODO (pending bench) | TODO (pending bench) | `reproduce:` TODO<br>`row:` TODO |
| R6 P40 (untested) | — | — | — | — |
| R7 Turing (untested) | — | — | — | — |

### B.3 — M3 (30B-class MoE, partial CPU offload)

Record the offload split (`-ngl` / expert placement) and host RAM in the row;
the number is meaningless without it.

| Row | 4k pp512 / tg128 | 16k pp512 / tg128 | 32k pp512 / tg128 | offload split | reproduce / row |
|---|---|---|---|---|---|
| R1 V100 PCIe | TODO (pending bench) | TODO (pending bench) | TODO (pending bench) | TODO | `reproduce:` TODO<br>`row:` TODO |
| R2 V100 SXM2 eGPU x4 | TODO (pending bench) | TODO (pending bench) | TODO (pending bench) | TODO | `reproduce:` TODO<br>`row:` TODO |
| R3 GTX 1060 (proxy) | TODO (pending bench) or n/a (VRAM) | TODO / n/a | TODO / n/a | TODO | `reproduce:` TODO<br>`row:` TODO |
| R4 MI50 16 GB | TODO (pending bench) | TODO (pending bench) | TODO (pending bench) | TODO | `reproduce:` TODO<br>`row:` TODO |
| R5 RTX 3060 (control) | TODO (pending bench) | TODO (pending bench) | TODO (pending bench) | TODO | `reproduce:` TODO<br>`row:` TODO |
| R6 P40 (untested) | — | — | — | — | — |
| R7 Turing (untested) | — | — | — | — | — |

---

## Column C — Serving aggregate (8 concurrent requests)

Only where vLLM (or the 1Cat-vLLM SM70 path / nlzy gfx906 fork) runs. If
it does not run, the cell is the **exact error string**, which is itself a
result.

| Row | Serving path | Aggregate tok/s (8-conc, M1) | Aggregate tok/s (8-conc, M2) | reproduce / row |
|---|---|---|---|---|
| R1 V100 PCIe | 1Cat-vLLM SM70 (evaluated) | TODO (pending bench) | TODO (pending bench) | `reproduce:` TODO<br>`row:` TODO |
| R2 V100 SXM2 eGPU x4 | 1Cat-vLLM SM70 (evaluated) | TODO (pending bench) | TODO (pending bench) | `reproduce:` TODO<br>`row:` TODO |
| R3 GTX 1060 (proxy) | TODO (bench plan: is there a working sm_61 serving path at all?) | TODO (pending bench) or error string | n/a (VRAM) | `reproduce:` TODO<br>`row:` TODO |
| R4 MI50 16 GB | nlzy vLLM gfx906 fork (pinned) | TODO (pending bench) | TODO (pending bench) | `reproduce:` TODO<br>`row:` TODO |
| R5 RTX 3060 (control) | vLLM latest | TODO (pending bench) | TODO (pending bench) | `reproduce:` TODO<br>`row:` TODO |
| R6 P40 (untested) | — | — | — | — |
| R7 Turing (untested) | — | — | — | — |

---

## Column D — Correctness delta

Two parts per row, per model. **Both** must pass.

| Row | M1 ppl Δ vs R5 (≤ 1 %) | M1 answers (3/3) | M2 ppl Δ vs R5 | M2 answers | M3 ppl Δ vs R5 | M3 answers | reproduce / row |
|---|---|---|---|---|---|---|---|
| R1 V100 PCIe | TODO (pending bench) | TODO | TODO | TODO | TODO | TODO | `reproduce:` TODO<br>`row:` TODO |
| R2 V100 SXM2 eGPU x4 | TODO (pending bench) | TODO | TODO | TODO | TODO | TODO | `reproduce:` TODO<br>`row:` TODO |
| R3 GTX 1060 (proxy) | TODO (pending bench) | TODO | n/a (VRAM) | n/a | TODO / n/a | TODO / n/a | `reproduce:` TODO<br>`row:` TODO |
| R4 MI50 16 GB | TODO (pending bench) | TODO | TODO | TODO | TODO | TODO | `reproduce:` TODO<br>`row:` TODO |
| R5 RTX 3060 (control) | 0 (reference) | TODO (must itself be 3/3) | 0 (reference) | TODO | 0 (reference) | TODO | `reproduce:` TODO<br>`row:` TODO |
| R6 P40 (untested) | — | — | — | — | — | — | — |
| R7 Turing (untested) | — | — | — | — | — | — | — |

Note on the control: the 3060's own 3/3 is a precondition. If the
reference fails the answer set, the fixture is wrong, not the cards.

---

## Column E — Vulkan (AMD rows only)

llama.cpp Vulkan backend, same card, same model, same quant, same contexts.
This is the honest baseline for every AMD cell in Column B: the question
is "how much does the HIP/ROCm path buy over the backend that never dropped
the card", not "does it run at all".

| Row | M1 Vulkan 4k pp512 / tg128 | M2 Vulkan 4k pp512 / tg128 | M3 Vulkan 4k pp512 / tg128 | HIP ÷ Vulkan (tg, M2) | reproduce / row |
|---|---|---|---|---|---|
| R4 MI50 16 GB | TODO (pending bench) | TODO (pending bench) | TODO (pending bench) | TODO | `reproduce:` TODO<br>`row:` TODO |
| (Radeon VII / Pro VII, untested) | — | — | — | — | — |

---

## Column F — tok/s per street dollar

`M2 tg128 @ 4k ÷ cited used price (USD)`. **No price citation, no
ratio.** Citation = source, listing type (sold / asking), date. Prices
move; the date is part of the number.

| Row | Street price (USD) | Citation (source, type, date) | M2 tg128 @ 4k | tok/s per $ | reproduce / row |
|---|---|---|---|---|---|
| R1 V100 PCIe 16 GB | TODO (cite) | TODO | TODO (pending bench) | TODO | `reproduce:` TODO |
| R2 V100 SXM2 32 GB + M.2 adapter | TODO (cite card + adapter separately) | TODO | TODO (pending bench) | TODO | `reproduce:` TODO |
| R3 GTX 1060 6 GB (proxy) | TODO (cite) | TODO | n/a (VRAM) | n/a | — |
| R4 MI50 16 GB | TODO (cite; note 16 GB vs 32 GB listings are different cards) | TODO | TODO (pending bench) | TODO | `reproduce:` TODO |
| R5 RTX 3060 12 GB | TODO (cite) | TODO | TODO (pending bench) | TODO | `reproduce:` TODO |
| R6 P40 24 GB (untested) | TODO (cite) — price only, no ratio | TODO | — | — | — |
| R7 Turing (untested) | — | — | — | — | — |

The lab's own purchase prices (what Scott paid) may be listed in a separate
"acquired for" column but are **not** the street price; they are one
person's pawn-shop and eBay luck.

---

## Column G — hw-attest score (optional)

If the hwattest tool is present on the bench host, its score is attached to
each row so a reader can see the measurement came off real silicon rather
than a VM or a spoofed arch string. Absent tool = empty cell, not a
failure.

| Row | hw-attest score | hwattest version | attached to rows | reproduce |
|---|---|---|---|---|
| R1 V100 PCIe | TODO | TODO | TODO | `reproduce:` TODO |
| R2 V100 SXM2 eGPU x4 | TODO | TODO | TODO | `reproduce:` TODO |
| R3 GTX 1060 (proxy) | TODO | TODO | TODO | `reproduce:` TODO |
| R4 MI50 16 GB | TODO | TODO | TODO | `reproduce:` TODO |
| R5 RTX 3060 (control) | TODO | TODO | TODO | `reproduce:` TODO |

---

## Reproduce-command skeleton

Every `reproduce:` slot above is filled with an invocation of this shape.
The bench plan supplies the concrete values; nothing is filled here.

```text
afterlife bench \
  --card <R1..R5> \
  --model <M1|M2|M3> --revision <sha> --quant <q> \
  --ctx <4096|16384|32768> \
  --pp 512 --tg 128 --warmup 1 --runs 3 \
  --power-cap <W> --clock-cap <MHz> \
  [--serve-concurrency 8 --serve-prompts bench/fixtures/serve_prompts.jsonl] \
  [--backend <cuda|hip|vulkan>] \
  [--offload <split spec>]            # M3 only
  --correctness bench/fixtures/ppl_text.txt bench/fixtures/answers.jsonl \
  --reference bench/rows/R5/<model>/<date>.json \
  --out bench/rows/<card>/<model>/<date>.json
```

Stock-latest cells (Column A) use the stock tool directly, and the slot
records the exact command *and* the exact version:

```text
# example shape only — versions and output are filled by the run
pip install --index-url <pytorch index> torch==<latest on bench date>   # record stderr verbatim
ollama --version && ollama run <M1 tag>                                  # record whether gfx906 / sm_70 is used or skipped
vllm serve <M1 id>                                                       # record the refusal string if any
rocminfo | grep -i gfx906                                                 # record support status
```

---

## Submitting a row

1. Run the reproduce command for the cell. Do not edit the flags; if the
   flags are wrong, change the bench plan and re-run.
2. Commit the JSON row (and CSV mirror) under `bench/rows/`.
3. Replace the cell's `TODO (pending bench)` with the median value, fill
   `reproduce:` with the exact command, and `row:` with the path.
4. Open a pull request. The PR must carry the row. **No rewards for matrix
   rows** — the row is the point.
5. A reviewer re-runs at least one cell from the PR on lab hardware before
   merge, when the hardware is available; otherwise the row merges with a
   `single-source` flag until a second run agrees.
