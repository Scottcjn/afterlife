# Afterlife — 60-second demo, shot list

Source: the Demo paragraph of the v0.1 spec. Target length 60 s ± 3. No
narration claims a number that is not on screen with its caveat.

**Standing on-screen disclosure (every shot where a tok/s figure appears):**

> Gemma 4 26B A4B is a Mixture-of-Experts model: ~4B parameters active per
> token. This is a 4B-active number, not a 26B-dense number.

Keep it as a persistent lower-third, not a flash card. HN will ask; we
answer before they do.

**Standing measurement caveat (same lower-third, second line):**

> Single lab measurement, V100 SXM2 32 GB over an M.2 eGPU adapter (PCIe
> Gen3 x4), 200 W / 1290 MHz cap. Not yet re-measured under the
> `afterlife bench` methodology. Reproduce command in docs/CLIFF_MATRIX.md.

Until a checked-in bench row exists for this cell, the figure on screen
reads **"~107 tok/s (lab, unverified)"** — never bare `107`.

---

## Hardware in frame

| Prop | What it is | On-screen label |
|---|---|---|
| Laptop | Gigabyte G6 KF, ~$600 used, i7-13620H, 32 GB DDR5, RTX 4060 8 GB internal | "$600 gaming laptop" |
| eGPU | Tesla V100 SXM2 32 GB on an SXM2 → M.2 adapter, PCIe Gen3 x4, external PSU, power-capped 200 W | "2017 V100 SXM2 32 GB, M.2 eGPU" |
| MI50 host | The lab box with the Radeon Instinct MI50 (**16 GB board** — Pro VII vBIOS) | "MI50, 16 GB board" |

The internal RTX 4060 must be visibly *not* the card doing the work:
`nvidia-smi` on screen with the 4060 idle and the V100 loaded.

---

## Shot list

| # | Time | Shot | On screen | Notes |
|---|---|---|---|---|
| 1 | 0:00–0:04 | Cold open. Hands plug the M.2 ribbon into the laptop; V100 on the desk beside it. | Title: **"Your datacenter GPU's vendor moved on."** | No voice yet. Natural sound. |
| 2 | 0:04–0:08 | Cut to terminal. `nvidia-smi` shows two GPUs: RTX 4060 (idle) and Tesla V100-SXM2-32GB. | Lower-third: "2017 V100 SXM2 32 GB · M.2 eGPU · PCIe Gen3 x4" | Prove the card is real before anything runs. |
| 3 | 0:08–0:18 | `llama-server` already up; chat request fires; tokens stream. The tok/s readout is visible in the server log, not pasted. | Lower-third (both lines): **4B-active MoE disclosure** + **"~107 tok/s (lab, unverified)"** caveat. Title: "Gemma 4 26B A4B" | 10 s of real streaming. Do not speed-ramp the stream. If the live run lands at a different number, the lower-third shows **that** number. |
| 4 | 0:18–0:21 | Hard cut. Same laptop, same card. Fresh venv. | Title: **"Same card. Stock path."** | Reset shot. |
| 5 | 0:21–0:27 | `pip install torch` (resolves to 2.15). Then a one-line CUDA check in Python → the unsupported-arch error, verbatim, un-cropped. | Title: "PyTorch 2.15 — sm_70 wheels dropped" | The error text is the shot. Hold long enough to read it. Record the actual string from the run; the title says what it is, the terminal says what it said. |
| 6 | 0:27–0:33 | `vllm serve …` on latest vLLM → refusal on compute capability 7.0, verbatim. | Title: "vLLM latest — refuses sm_70" | Same rule: real string, un-cropped. |
| 7 | 0:33–0:36 | Fast montage (3 cards, 1 s each): CUDA 13 release note line dropping sm_70; R580 "last branch" line; ROCm 7 gfx906 "unsupported" line. | Title: **"CUDA 13 · R580 · ROCm 7 — all moved on."** | Each card shows the source doc, not a paraphrase. Cite in the video description. |
| 8 | 0:36–0:46 | `afterlife doctor`. Output: detected card (V100, sm_70), installed driver/toolkit/framework, each cliff it hits, and the exact fix line per cliff. Then `afterlife doctor --fix` (or the printed install line) runs; pinned torch 2.14.0 cu126 installs; the same CUDA check from shot 5 now prints the device name. | Title: **"`afterlife doctor` — what broke, and the last stack that works."** | This is the product shot. Doctor output should be legible at 1080p; use a large terminal font. |
| 9 | 0:46–0:50 | Cut back to streaming tokens on the V100 (same as shot 3, short). | Lower-third: disclosure + caveat still up. Title: "Running." | 4 s. No new number introduced. |
| 10 | 0:50–0:57 | Split screen. **Left:** MI50 host, `ollama run <model>` on latest Ollama — log shows gfx906 skipped / falling back to CPU, verbatim. **Right:** same host, Afterlife gfx906 stack (llama.cpp HIP, or Vulkan if that is what the bench plan ships), tokens streaming. | Left title: "Ollama 0.13 — gfx906 skipped". Right title: "Afterlife — MI50 (16 GB board)". Lower-third right: tok/s **only if a bench row exists**; otherwise no number, just the stream. | Say "16 GB board" on screen. Do not put an MI50 tok/s figure up without a checked-in row; the Strata/`strata906` numbers are unpublished lab measurements and stay out of the video. |
| 11 | 0:57–1:00 | End card. | **"Afterlife. Pinned, tested, honest-limits-first."** Repo URL. One line: "All numbers: docs/CLIFF_MATRIX.md, every cell has a reproduce command." | Hold 3 s. |

---

## Rules for the edit

1. **Every number on screen has its caveat on screen at the same time.**
   No number is introduced in narration alone.
2. **Error strings are shown verbatim and un-cropped.** The whole point is
   that the stock path says what it says.
3. **No speed-ramping the token stream.** If it is slow, it is slow.
4. **No MI50 tok/s figure** until a bench row for R4 exists.
5. **The 4060 is visibly idle** in the eGPU shots (`nvidia-smi` util column).
6. **Pre-flight before recording (not an agent task; Scott on the lab
   machines):**
   - Confirm the V100 enumerates after a cold plug (it has fallen off the bus
     in a different host before; record a `dmesg` tail in case it does).
   - Confirm `v100-tame` is active (200 W / 1290 MHz) and say so in the
     caveat, because the number depends on it.
   - Run shot 5 and shot 6 once off-camera to capture the exact error
     strings; they go into the video description as text.
   - `pgrep` for an existing `llama-server` / Ollama before launching
     anything; two servers on one card makes a bad shot and a worse number.
7. **Description text (below the video) must include:** the 4B-active MoE
   line, the "single lab measurement, unverified" line, the hardware list
   above, the link to [CLIFF_MATRIX.md](CLIFF_MATRIX.md), and the upstream
   credits from the [README](../README.md#credits-upstream).

---

## What this demo does NOT claim

- That 107 tok/s is reproducible (it is a lab observation pending the bench).
- That the 26B is comparable to a 26B dense model (it is a 4B-active MoE).
- That the MI50 is a 32 GB card (it is running as 16 GB).
- That the eGPU result matches a PCIe x16 V100 (it is Gen3 x4).
- Anything about P40 (we have a GTX 1060 proxy, and it is not in this video).
