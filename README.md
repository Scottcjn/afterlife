# Afterlife

**A pinned, tested inference stack for datacenter GPUs their vendors stopped shipping for.**

Status: **v0.1 pre-release, unbenchmarked.** Nothing in this repository has
been published, and every performance cell in the matrix below is a template
slot waiting for a measurement. Read the limits before the pitch.

---

## Honest limits first

Read these before anything else. They are not footnotes.

1. **No verified numbers yet.** The cliff matrix in this README and in
   [docs/CLIFF_MATRIX.md](docs/CLIFF_MATRIX.md) is a *template*. Every tok/s
   cell reads `TODO (pending bench)` and carries an empty `reproduce:` slot.
   A cell gets a number only when the command in its slot has been run and
   the JSON row from `afterlife bench` is checked in next to it. The
   bench plan that fills the matrix
   ([eval/BENCH_FLEET_PLAN.md](eval/BENCH_FLEET_PLAN.md)) is Scott's to run
   on lab hardware, not an agent's.
2. **The headline figure is an unpublished lab measurement.** "Gemma 4 26B at
   ~107 tok/s on a V100 SXM2 32 GB over an M.2 eGPU adapter" was observed
   once, in the Elyan Labs workshop, on a `llama-server` build with a 200 W /
   1290 MHz power-and-clock cap. It has **not** been re-measured with the
   `afterlife bench` methodology, has no checked-in JSON row, and has not been
   reproduced by anyone outside the lab. Treat it as a reason to run the
   bench, not as a result.
3. **Gemma 4 26B A4B is a Mixture-of-Experts model with ~4B active
   parameters per token.** Decode speed on a 26B MoE with 4B active is not
   comparable to a 26B dense model. Any number quoted for it is a 4B-active
   number. We say this first so nobody has to discover it in the comments.
4. **The Pascal row is a proxy.** We do not own a Tesla P40. The sm_61 row
   uses a **GTX 1060 6 GB** as a stand-in for P40 / Pascal. Same compute
   capability, same driver and toolkit cliff, different memory size, bus,
   cooling and power envelope. Results on a 1060 do not transfer to a P40
   without someone running the reproduce command on a P40.
5. **The MI50 row is a 16 GB board.** The lab's MI50 is a 32 GB-labelled
   board whose PSP rejects every 32 GB image; it runs on the 16 GB Radeon Pro
   VII vBIOS and that is what it is. All gfx906 cells are 16 GB results.
   Every MI50 32 GB number you have seen elsewhere is a different card.
6. **The eGPU V100 is a PCIe Gen3 x4 link** (M.2 adapter). Prompt-processing
   and multi-request serving on it are bandwidth-starved in ways a PCIe x16
   V100 is not. Those cells are labelled `eGPU x4` and are not a V100 PCIe
   x16 result.
7. **Scope is v0.1.** Three stranded architectures (sm_70, sm_61 proxy,
   gfx906) and one supported control (RTX 3060, sm_86). No new kernels. No
   training beyond a smoke test. No Windows. No Turing (sm_75) until v0.2; it
   is next on the cut list and we know it.
8. **Redistribution.** No container image is published until the CUDA and
   ROCm redistribution terms have been checked for each bundled component.
   Where the terms are unclear, Afterlife ships a build-from-recipe, not an
   image.
9. **We consolidate; we do not compete.** The gfx906 and sm_70 paths exist
   because of other people's work. See [Credits](#credits-upstream).

---

## The pitch

> Your datacenter GPU's vendor moved on. You don't have to.
>
> Gemma 4 26B at ~107 tok/s on a 2017 V100 plugged into a laptop.
> CUDA 13, PyTorch 2.15, vLLM and ROCm 7 all dropped these cards;
> `afterlife doctor` tells you what broke and installs the last stack that
> works.

(The 107 figure is limit #2 above. The 26B is limit #3. We mean it.)

### What Afterlife ships

| Piece | What it does |
|---|---|
| **`afterlife doctor`** | Reads `nvidia-smi` / `rocminfo` / `lspci`, compares your installed driver, toolkit and framework against a versioned **cliff database** (YAML), and prints exactly what will break on your card and the exact fix. |
| **Pinned manifests + containers per arch** | NVIDIA legacy: R580 + CUDA 12.9 + torch 2.14.0 (cu126) + llama.cpp built for sm_70/sm_61 + an evaluated vLLM path starting from 1Cat-vLLM's SM70 wheel. gfx906: TheRock 7.12 nightly or ROCm 6.4.x with restored Tensile files + llama.cpp HIP + Vulkan fallback + a pinned vLLM fork. |
| **`afterlife bench`** | A fixed-methodology runner that writes one JSON/CSV row per run: model, quant, flags, driver, power cap, pp512 / tg128 at 4k / 16k / 32k context, an 8-concurrent serving number where vLLM works, and a correctness gate. |

### The cliff database (what the doctor checks against)

| Cliff | What dropped | Last version that works |
|---|---|---|
| CUDA 13 | sm_50 through sm_70 | CUDA 12.9 |
| NVIDIA driver | Volta / Pascal | R580 (last branch) |
| PyTorch 2.15 | sm_70 / sm_61 wheels | torch 2.14.0 (cu126) |
| vLLM (latest) | V100 / sm_70 | 1Cat-vLLM SM70 wheel (evaluated path) |
| ROCm 7 | gfx906 unsupported | ROCm 6.4.x (+ restored Tensile) / TheRock 7.12 nightly |
| Ollama 0.13 | gfx906 | 0.12.x, or llama.cpp HIP / Vulkan directly |

The YAML database lives at
[afterlife/cliff_db.yaml](afterlife/cliff_db.yaml) and is versioned with
the repo so a doctor run can be reproduced against the database revision it
used.

---

## Cliff matrix (template, v0.1)

The full matrix, with every column and a `reproduce:` slot per cell, is in
[docs/CLIFF_MATRIX.md](docs/CLIFF_MATRIX.md). This is the short form. **A
cell without a reproduce command stays `TODO`. No exceptions.**

Three fixed open-licence reference models (final picks and exact revisions
are pinned in the bench plan; license files + `LICENSE_RECEIPT.txt` ship
with each):

- **M1** — dense, ~8B class
- **M2** — Gemma 4 26B A4B, a **4B-active MoE** (or a ~27B dense alternate if the bench plan swaps it)
- **M3** — 30B-class MoE, with partial CPU offload

| Card (arch) | Legend | Stock-latest result | Afterlife M1 pp512 / tg128 | Afterlife M2 pp512 / tg128 | Afterlife M3 pp512 / tg128 | Serving 8-conc | Correctness delta |
|---|---|---|---|---|---|---|---|
| V100 PCIe 16 GB (sm_70) | supported | TODO (pending bench) | TODO (pending bench) | TODO (pending bench) | TODO (pending bench) | TODO (pending bench) | TODO (pending bench) |
| V100 SXM2 32 GB, eGPU x4 (sm_70) | supported, eGPU x4 | TODO (pending bench) | TODO (pending bench) | TODO (pending bench) — lab-only ~107 tok/s, unverified | TODO (pending bench) | TODO (pending bench) | TODO (pending bench) |
| GTX 1060 6 GB (sm_61) | **proxy** for P40 | TODO (pending bench) | TODO (pending bench) | n/a (VRAM) | n/a (VRAM) | n/a | TODO (pending bench) |
| MI50 16 GB (gfx906) | supported, 16 GB board | TODO (pending bench) | TODO (pending bench) | TODO (pending bench) | TODO (pending bench) | TODO (pending bench) | TODO (pending bench) |
| RTX 3060 12 GB (sm_86) | **control** | TODO (pending bench) | TODO (pending bench) | TODO (pending bench) | TODO (pending bench) | TODO (pending bench) | reference (0 by definition) |
| Tesla P40 24 GB (sm_61) | **untested** | — | — | — | — | — | — |
| Turing (sm_75) | **untested**, v0.2 | — | — | — | — | — | — |

AMD rows also get a **Vulkan** column and every row gets a
**tok/s per street dollar** column (prices cited, dated) in the full matrix.

### Legend

| Mark | Meaning |
|---|---|
| **supported** | We own the card, the pinned stack builds on it, and every cell has (or will have) a checked-in reproduce row. |
| **proxy** | Same compute capability as the card it stands in for, but a different board. Results do not transfer without a run on the real card. |
| **control** | A card the vendors still support. The correctness reference and the "how much are we losing" baseline. |
| **untested** | Listed because the cliff database covers it. No hardware, no numbers, no claims. |
| **eGPU x4** | PCIe Gen3 x4 over an M.2 adapter. Not a x16 result. |
| **lab-only** | A single workshop observation with no bench row. Not a result. |

---

## Methodology

Every number that ever enters the matrix is produced by `afterlife bench`
under these fixed rules. If a row was produced any other way it does not go
in.

- **Runner.** `afterlife bench` writes one JSON row (and a CSV mirror) per
  run containing: card, arch, driver branch, toolkit, framework + commit,
  model id + revision sha, quant, every runtime flag, **power cap and clock
  cap** (set and reported), ambient-ish temperature at start, and the
  timestamp.
- **Prompt processing / generation.** `pp512` and `tg128`, each at **4k,
  16k and 32k** context, 3 warm runs after 1 discarded warm-up, median
  reported, min/max kept in the row.
- **Serving.** Where vLLM (or the 1Cat SM70 path) runs, an **8 concurrent
  request** aggregate tok/s with a fixed prompt set. Where it does not run,
  the cell says which error, verbatim.
- **Stock-latest column.** For each of Ollama, vLLM, PyTorch and official
  ROCm at their latest release on the bench date: **runs**, **runs slow**
  (with the number), or the **exact error string**. Version and date are
  recorded in the row.
- **Correctness gate.** Two parts, both required:
  1. Perplexity on a fixed text versus the **RTX 3060 reference**, must be
     within **1 %**.
  2. **3 / 3** on a fixed short answer set.
  A row that fails either is marked `FAIL` in the correctness column and its
  tok/s cells are shown struck through. "Fast but broken" is not a result.
- **Vulkan column (AMD).** Every AMD row is compared against llama.cpp
  Vulkan on the same card, same model, same quant. The honest comparison is
  against Vulkan, not against nothing.
- **tok/s per street dollar.** M2 tg128 at 4k divided by a **cited, dated**
  used-market price. The citation (source, date, listing type) is part of
  the cell. No price, no ratio.
- **hw-attest score (optional).** If the hwattest tool is installed, its
  score is attached to the row so a reader can see the measurement came off
  real silicon.
- **Public table by pull request only.** Rows enter the public matrix via PR
  with the JSON row attached. No rewards, no bounties, for matrix rows.

The command skeleton per cell is in
[docs/CLIFF_MATRIX.md](docs/CLIFF_MATRIX.md). Each one is a
`reproduce:` slot that the bench plan fills in with the exact invocation.
The runner itself is documented in
[afterlife/bench/README.md](afterlife/bench/README.md); its table builder
refuses to emit a row that has no `reproduce_cmd`, so the "no command, no
number" rule is enforced by code, not by reviewers remembering it. The
runner's own CPU self-test uses a mock backend whose throughput is
synthetic filler and is never a measurement of any card.

---

## Demo

A 60-second video, shot list in [docs/DEMO_SCRIPT.md](docs/DEMO_SCRIPT.md):
a $600 gaming laptop with a V100 SXM2 32 GB on an M.2 adapter running Gemma
4 26B A4B; the same card on the stock path failing (`pip install torch`
2.15 unsupported-arch, latest vLLM refusing sm_70); `afterlife doctor`
naming the breaks and fixing them; and the MI50 on stock Ollama (skipped)
next to Afterlife. The "26B is a 4B-active MoE" disclosure is on screen
whenever a number is.

---

## Supported, proxy, untested — per card

| Card | Arch | Status | Notes |
|---|---|---|---|
| Tesla V100 PCIe 16 GB | sm_70 | supported | In the lab (Dell C4130). |
| Tesla V100 SXM2 32 GB | sm_70 | supported (eGPU x4) | M.2 → SXM2 adapter in a laptop; PCIe Gen3 x4; tamed to 200 W / 1290 MHz. |
| GTX 1060 6 GB | sm_61 | proxy (for P40 / Pascal) | 6 GB limits which models fit. Cells that do not fit say `n/a (VRAM)`. |
| Tesla P40 24 GB | sm_61 | untested | Not owned. Cliff database covers it; no numbers. |
| Radeon Instinct MI50 | gfx906 | supported (16 GB board) | Runs on the 16 GB Radeon Pro VII vBIOS; PSP rejects 32 GB images. |
| Radeon VII / Radeon Pro VII | gfx906 | untested | Same silicon family as the MI50; not yet on the bench. |
| RTX 3060 12 GB | sm_86 | control | Vendor-supported. Correctness reference. |
| Turing (T4, RTX 20xx) | sm_75 | untested, v0.2 | Next on the cut list; queued, not promised. |

---

## Non-goals (v0.1)

New kernels. Training support beyond a smoke test. Windows. Turing. A
public container registry before the redistribution review. Benchmarks run
by anything other than the fixed runner.

---

## Credits (upstream)

Afterlife is a consolidation. The hard parts were done by:

- **1Cat-vLLM** — the SM70 vLLM wheel that the NVIDIA legacy serving path
  starts from.
- **mixa3607** — `rocm-gfx906` Docker images (ROCm 7.14 / 10.x with gfx906
  rocBLAS/hipBLAS) and the `strata-gfx906` images; the reason the gfx906 row
  exists at all.
- **nlzy** — the pinned vLLM fork for gfx906.
- **TheRock** — the ROCm-from-source build system that the 7.12 nightly
  path uses.
- **Atlas3D** — named in the build rules as an sm_70 llama.cpp fork, but the
  prior-art search ([docs/PRIOR_ART.md](docs/PRIOR_ART.md)) **could not
  locate a repository** under that name. The credit stays here as a pointer
  until a URL exists; nothing in the stack cites it yet.

Full prior-art notes, with repo links, licenses and what each one gives
us, are in [docs/PRIOR_ART.md](docs/PRIOR_ART.md).
- **llama.cpp** (ggml-org) and the Vulkan backend it ships, which is the
  honest baseline for every AMD row.

If your work belongs here and is missing, open an issue; we would rather
over-credit than under-credit.

---

## License

Apache-2.0. See [LICENSE](LICENSE). Cite with [CITATION.cff](CITATION.cff).

Reference models are pulled with their own LICENSE / NOTICE / model card and
a `LICENSE_RECEIPT.txt` (repo id, revision sha, download date, license name,
sha256 of each license file, terms relied on). Gated licenses are accepted by
a human, never by an agent.
