# Afterlife cliff-matrix: fleet bench plan (SERIAL, for Scott to execute)

Status: PLAN ONLY, written 2026-11-06. Nothing here has been run. No SSH, no GPU, no push was done in writing it.
Target: SPEC.md "cliff matrix" (stock-latest result per tool, Afterlife pp/tg for 3 models, serving aggregate, correctness delta, Vulkan column on AMD, tok/s per used dollar).
Rule that governs everything below: **a striking result is a probe artifact until a second, different probe agrees.** That is a hard gate between every step, not advice.

Credentials are deliberately NOT written here. Take them from /home/scott/CLAUDE.md and the memory files named per host. Never paste them into agent prompts, scripts, or result files.
NEVER touch RustChain nodes <rustchain-node> / <rustchain-node>. Nothing in this plan needs them.

---------------------------------------------------------------------
## 0. Read this first: what is and is not known

| Item | State |
|---|---|
| `afterlife bench` CLI | Does not exist yet in repo (only skeleton). Every `afterlife bench` line below uses PROVISIONAL flag names. For each, a raw `llama-bench` / `llama-perplexity` fallback is given that you can run today. If the CLI flags differ when built, the fallback is the truth. |
| ~107 tok/s eGPU V100 (Gemma 4 26B A4B on G6 KF) | UNPUBLISHED lab measurement, from a service on :8080. Method, prompt length, context, and whether it is pp or tg are not recorded in what I read. **Must be independently re-measured (section 6.3) before it appears anywhere.** Also it is a 4B-active MoE; say so. |
| MI50 Strata numbers (12-16 tok/s, 3/3 correct, on .191) | UNPUBLISHED lab measurement. They were taken over a PCIe Gen1 x4 chipset link (finding-191-mi50-on-gen1-x4-chipset-slot.md; Aug 2026; I do not know if it was fixed since). Re-measure; record the link speed with every row. |
| Cliff claims (CUDA 13 drops sm_50-70, torch 2.15 drops sm_70/61, vLLM dropped V100, Ollama 0.13 dropped gfx906, ROCm gfx906 unsupported) | Taken from SPEC. NOT verified by me. The stock-path capture steps below exist to make them real or to show they are wrong. If a capture shows the tool still works, the cell says "runs" and the SPEC/README claim is corrected. |
| Where a GTX 1060 physically is | NOT FOUND in memory or CLAUDE.md (only "GTX 1060 x2+ in the bench reserve"). **Needs a host.** See card E. |
| `~/llm/GPU_LOCK` | Exists on the A51 R5 (.150) per memory. Does not exist on the Victus (I checked /home/scott/llm). Check each remote host, do not assume. |

---------------------------------------------------------------------
## 1. Order of operations (SERIAL: one card at a time, never two benches in parallel)

1. **Card A: RTX 3060 (control) on A51 R5 .150.** First, because every other card's correctness delta needs its reference numbers.
2. **Card B: V100 16GB PCIe on C4130 #1 .161.**
3. **Card C: V100 SXM2 32GB eGPU on G6 KF.** Needs Scott to stop the demo service. Do on a day with no demo.
4. **Card D: MI50 / gfx906 on .191.** Needs hands (link speed) and agreement on what is running there.
5. **Card E: GTX 1060 (Pascal proxy).** Needs a host; last because it needs hardware moved.

**Gate G between every card (all must be true before the next card starts):**
- [ ] All result files for this card are copied back to the Victus under `eval/results/<card>/<UTC-date>/` and committed LOCALLY (no push).
- [ ] Every cell has its exact command next to it (the command log, section 4.4).
- [ ] Every cell that looks surprising (see 6.1 triggers) has a second probe that agrees, or is marked `UNCONFIRMED` and kept out of the README table.
- [ ] Correctness gate (section 5) passed or its failure is recorded as a result, not hidden.
- [ ] GPU returned to its prior state: services restarted, locks released, power limits restored to what you recorded in pre-flight.
- [ ] `dmesg`/Xid/AER delta is empty or explained (section 4.2).

If any box fails: STOP the fleet run. Do not move on to look at "another card" to make progress.

---------------------------------------------------------------------
## 2. Common pre-flight (every card, every session)

Run on the target host. Save the output to the result dir; it is part of the receipt.

```bash
# 2.1 who/what is on this machine right now
hostnamectl; uptime; who
pgrep -af 'llama|ollama|vllm|comfy|python|rpc-server|strata|exllama|tabby' | grep -v pgrep
# running worker for our own script name (lab rule: check before starting)
pgrep -af 'afterlife|llama-bench|llama-perplexity|llama-server' | grep -v pgrep   # must be empty before you start

# 2.2 locks and other users
ls -la ~/llm/GPU_LOCK 2>/dev/null && cat ~/llm/GPU_LOCK      # if present and not FREE: STOP, ask Scott
nvidia-smi --query-compute-apps=pid,process_name,used_memory --format=csv   # NVIDIA: must be empty for the card under test
# AMD:  rocm-smi --showpids ; fuser -v /dev/kfd /dev/dri/* 2>&1   (fuser misses docker: also `docker ps`)
docker ps --format '{{.Names}} {{.Image}} {{.Status}}' 2>/dev/null

# 2.3 baseline telemetry and state to restore later
nvidia-smi -q -d POWER,CLOCK,PERFORMANCE,TEMPERATURE > preflight_nvsmi.txt     # AMD: rocm-smi -a > preflight_rocm.txt
nvidia-smi --query-gpu=index,name,driver_version,pcie.link.gen.current,pcie.link.width.current,power.limit,power.default_limit,temperature.gpu --format=csv
dmesg -T 2>/dev/null | grep -ciE 'xid|aer|nvrm|amdgpu.*(error|fault)' | tee preflight_dmesg_count.txt
df -h . ; free -g
```

Hard stops, any one means do not start:
- `GPU_LOCK` present and not FREE, or any non-ours process on the card under test.
- A shared service (below, per card) is running that you have not been told you may stop.
- Free disk under 40 GB (models are 5-20 GB each; stock-path venvs are 5-10 GB).
- `5070 = elya_library lock note`: on the A51 R5 the **GPU1 / RTX 5070 is normally held by the elya_library Wan render node (ComfyUI :8188) and the Crust Pizza holo render host. Do not use or evict it.** This plan only uses the 3060s (GPU0 and GPU2) on that host. Do not `pkill` anything; probe, then lock.
- Writing the lock when it is free: `echo "afterlife-bench <card> $(date -u +%FT%TZ) scott-session" > ~/llm/GPU_LOCK`, and set it back to `FREE` at the end (match the existing file format if it differs; read it first).

Files and working dirs: put everything under `~/afterlife-bench/<UTC-date>/` on the target, never `/tmp` (tmpfs, wiped, lab OOM incident 10/1). Keep stock-path trials in their own throwaway dirs, run any Python on downloaded artifacts with `python -I`.

---------------------------------------------------------------------
## 3. Cards: host, access, specifics

Access strings reference where the secret lives; none are written here.

### Card A: RTX 3060 12GB, correctness-reference control (arch sm_86)
- **Host:** A51 R5 "elyan-a51", LAN <lab-host>, Tailscale <tailnet-host>. GPU0 = RTX 3060 12GB, GPU2 = RTX 3060 12GB. **Never GPU1 (5070).**
- **Access:** user `powerelyan`; password-only SSH or it fails on MaxAuthTries. See memory `project-a51-r5-hypercore-exl3-2026-11-05.md` for the password and the exact options:
  `ssh -o PreferredAuthentications=password -o PubkeyAuthentication=no -o IdentitiesOnly=yes powerelyan@<lab-host>`
- **Extra pre-flight:** `cat ~/llm/GPU_LOCK` (must be FREE), `nvidia-smi` shows who holds GPU1 (leave it alone), `free -g` (31 GB RAM is the bottleneck here; the Wan lowvram node uses ~26 GB of it. If ComfyUI :8188 is running, free RAM is too small for the 30B MoE CPU-offload row. Mark that row `NOT RUN (RAM)` instead of asking to stop the render node. Ask Scott first if you want to stop it.)
- **Pin to one card:** `export CUDA_VISIBLE_DEVICES=0` for every command. For the variance check repeat once on GPU2.
- **Role:** the reference. If the 3060 numbers are themselves unstable (two runs differ over 3%), fix that before using it as the gate.

### Card B: V100-PCIE 16GB (sm_70)
- **Host:** Dell C4130 #1, LAN <lab-host> (40GbE 10.40.0.2). 2x V100-PCIE-16GB (verified 2026-10-14). 31 GB RAM. Use ONE card: `CUDA_VISIBLE_DEVICES=0`.
- **Access:** user `sophiacord2`, see CLAUDE.md "Dell PowerEdge C4130 Configuration" for the password. `ssh sophiacord2@<lab-host>`.
- **Shared services to check (do not stop without Scott):** `rpc-server` (port 50052) and `matmul_persistent.py` (port 8096) used by the POWER8 offload; `pgrep -af 'rpc-server|matmul'`; `ss -ltnp | grep -E '50052|8096'`. If either is live and in use, ask. Prefer the GPU not in use; check `nvidia-smi` memory.
- Do NOT use .160 (NAS): it runs the production Sophiacord bot on its two V100s.
- Stock `nvidia_drm` is blacklisted on this box (compute only); do not load it.
- P2P note (memory): iommu=pt fixed GPU0<->GPU1 copies on 2026-10-15. Irrelevant to single-card bench; do not run two cards.

### Card C: V100 SXM2 32GB over M.2 eGPU, Gen3 x4 (sm_70) , the demo card
- **Host:** Gigabyte G6 KF "elya-g6-demo", LAN .147, Tailscale **<tailnet-host>**, user `elya`, default SSH key. Sudo non-interactively: `~/.elyan-secrets/g6kf-elya-sudo-askpass | ssh -o BatchMode=yes elya@<tailnet-host> 'sudo -S -p "" <cmd>'` (see memory reference-g6kf-sudo-askpass.md; never paste the password). Run the ssh/sudo from the Victus.
- **GPUs:** RTX 4060 8GB (internal) + V100 SXM2 32GB (eGPU). Driver 580, CUDA 12.9. **Identify the V100 by name/UUID, never by index** (index 0/1 may differ after reboot): `nvidia-smi -L`, then `CUDA_VISIBLE_DEVICES=<V100-UUID>` so the 4060 is invisible to every bench.
- **Shared services to deal with:** `elya-llm.service` (Gemma 4 26B A4B on the V100, :8080) is what Scott demos. It occupies the card. **Scott stops it** (`sudo systemctl stop elya-llm.service`) and restarts it after (`... start`); record `systemctl is-active` before and after. `v100-tame.service` sets 200 W / 1290 MHz; leave it as is for the "as deployed" run (section 3 power caps).
- **Fault history, treat as a validity condition:** the SXM2 V100 "fell off the bus" in the A51 R2, and memory notes ~5 AER/min on this link with 0 Xid. Record `dmesg` AER/Xid counts before and after each run; any NEW Xid, or a card that drops out mid-run, voids the run (record it as a result; it is a finding about the platform, not noise).
- Link is Gen3 x4: record `pcie.link.gen.current/width.current` under load (it can renegotiate down at idle).
- OCuLink/M.2 eGPU is not hot-pluggable: do not touch cabling during a session.
- Thermals: laptop chassis + eGPU. Log temp every second during the run (section 4.3). If temp passes the card's throttle point the run is a thermals result; record it.

### Card D: MI50 / Radeon Pro VII, gfx906, 16 GB
- **Host:** `.191` "elyan-havoc" (Ryzen 9 7900X), LAN <lab-host> or patchcord 10.42.0.2. User `scott` (password in memory project-191-dual-amd-dense.md). SSH key auth refused; password login works. Use `-o UserKnownHostsFile=/dev/null`; SFTP subsystem is broken, so `scp` fails: **pipe over ssh** (`ssh host 'cat file' > local`, `tar c ... | ssh`). Memory also says it can be reached through a .160 Tailscale jump.
- **It is a 16 GB board, not 32.** (Reflash attempt closed, original restored. Label it 16 GB.)
- **Known invalidity risk:** the card sat behind a chipset slot negotiated at **PCIe Gen1 x4 (0.8 GB/s)** as of 2026-08-20. Record the current link first: `lspci -vv -s 08:00.0 | grep -E 'LnkCap|LnkSta'` and `lspci -tv`, plus the kernel line `dmesg | grep 'limited by'`. Weights load across that link once, so tg once resident is mostly unaffected but load time and any offload row are crushed. Label every AMD row with the measured link. If it is still Gen1 x4, the 30B-MoE CPU-offload row is meaningless for AMD (mark `N/A: link-bound`) unless Scott fixes the slot (BIOS/reseat, needs hands).
- **Other tenants (ask before touching, do not stop blind):** `ollama-dual` (systemd, ollama service), RX 9060 XT (gfx1200) ComfyUI job, the Strata container `strata906` (image mixa3607/strata-gfx906), `john-miner-191` / John corpus worker. Use `docker ps`, `systemctl list-units | grep -iE 'ollama|comfy|john|strata'`. The MI50 must be idle: `rocm-smi --showuse --showmemuse`.
- Kernel pinned to 146 (147 needs newer amdgpu-dkms); do not run `apt upgrade` or install kernels.
- Pin devices: `HIP_VISIBLE_DEVICES=<index of gfx906>` (find via `rocminfo | grep -E 'Name:.*gfx'` or `rocm-smi --showproductname`; ROCm userspace 6.3.3 on this box can show an empty `rocminfo` due to KFD skew, so confirm with `rocm-smi`). The 9060 XT must be invisible to every bench.

### Card E: GTX 1060 (sm_61), proxy for P40 / Pascal
- **Host: NEEDS A HOST.** Memory only says "GTX 1060 6GB x2+ in the bench reserve." Not installed anywhere I could find. Candidate: the i7-8700K tower **.187** (850W PSU, RTX 2070 pulled, boots on iGPU; user in CLAUDE.md), because it has a free slot and PSU. Constraints to know first: that box has **16 GB DDR4 RAM**, so the 30B-class MoE offload row cannot hold Q4 weights in RAM (about 18 GB) and must be `N/A (host RAM)`; 6 GB VRAM means the ~26B row is also heavy-offload or N/A. State both honestly.
- This is a **proxy**. A GTX 1060 is sm_61 like the P40 but has 6 GB (vs 24 GB), GDDR5 and different FP16/DP4A throughput. The README legend must say "proxy" and never present 1060 numbers as P40 numbers.
- Needs Scott's hands: install card, power leads, Ubuntu driver 580 branch state check. Do not change the driver on .187 (it is also a miner / Lantern host, see memory) without asking.

---------------------------------------------------------------------
## 4. Method common to all cards

### 4.1 Build and pin (done once per arch, before the bench session)
Build llama.cpp from one pinned commit (record `git rev-parse HEAD`) per arch:
```bash
# NVIDIA (set the arch for the card: 61, 70, 86)
cmake -B build-cuda -DGGML_CUDA=ON -DCMAKE_CUDA_ARCHITECTURES=70 -DCMAKE_BUILD_TYPE=Release
cmake --build build-cuda -j$(nproc) --target llama-bench llama-perplexity llama-server llama-batched-bench
# AMD HIP:    cmake -B build-hip -DGGML_HIP=ON -DAMDGPU_TARGETS=gfx906 ...
# AMD Vulkan: cmake -B build-vk  -DGGML_VULKAN=ON ...
```
Record: commit sha, compiler, CUDA/ROCm version, driver, build flags. The same commit is used on all cards so differences are hardware/arch, not source. The 3060 reference build uses that same commit.

### 4.2 Validity checks wrapped around every run
```bash
# before
dmesg -T | grep -ciE 'xid|aer|nvrm|amdgpu.*(error|fault)' > dmesg_before.txt
# after
dmesg -T | grep -ciE 'xid|aer|nvrm|amdgpu.*(error|fault)' > dmesg_after.txt   # differ => explain or void
```
Repeat every cell 3 times; report median and spread. Spread over 5% means the cell is unstable: investigate (clocks, thermals, other load), do not average it away.

### 4.3 Concurrent telemetry (run in a second ssh session, kill ONLY that PID)
```bash
nvidia-smi --query-gpu=timestamp,power.draw,clocks.sm,clocks.mem,temperature.gpu,pcie.link.gen.current,pcie.link.width.current,clocks_throttle_reasons.active --format=csv -l 1 > telem.csv & echo $! > telem.pid
# stop: kill "$(cat telem.pid)"   (never pkill/killall by name; shared tools)
# AMD: while sleep 1; do rocm-smi --showpower --showtemp --showclocks --csv; done > telem.csv & echo $! > telem.pid
```

### 4.4 Command log
Wrap every bench command so the exact command line, env, and git sha are saved: `script -q -c '<cmd>' cmdlog_<cell>.txt` or `( set -x; <cmd> ) 2>&1 | tee cmdlog_<cell>.txt`. The "reproduce" column in the matrix is read straight from these. A cell with no command log stays out of the README.

### 4.5 Models (three fixed open-licence models, same GGUF file, same sha256 on every card)
Rule 0 of CLAUDE.md applies: each model folder gets LICENSE*/NOTICE*/model card plus `LICENSE_RECEIPT.txt` (repo id, exact revision sha, UTC date, account used, license name, sha256 of each license file, terms we rely on). Gated licenses are accepted by Scott only. Download once on the Victus or one host, verify `sha256sum`, copy; do not re-download per card.

| Slot | Proposed model | Quant | Why / caveat |
|---|---|---|---|
| Dense ~8B | An Apache/MIT-licence 8B instruct (proposal: Qwen3-8B or a Gemma-class 8B; Scott's note: prefers US models for the demo box, so confirm) | Q4_K_M | Fits all five cards incl. 6 GB 1060 (barely, short context). Final repo id + sha are decided at download and written into the receipt. |
| ~26-27B | **Gemma 4 26B A4B** (already on the G6 KF as QAT; MoE, ~4B active. Say "MoE, 4B active" in the table) | the QAT/Q4 file already used, or Q4_K_M | Q4 is about 15-16 GB, so it does NOT fit a 16 GB card with 32k KV. On 16 GB cards: use reduced context or partial offload and say so in the cell. Note if a 27B *dense* is wanted instead, it will OOM on 16 GB at long context. |
| 30B-class MoE, partial CPU offload | proposal: Qwen3-30B-A3B (Apache-2.0) | Q4_K_M | `--n-cpu-moe` (or `-ot` expert regex) to keep experts on CPU. Needs ~18 GB host RAM free. N/A on .187 (16 GB) and on .150 while the Wan node holds RAM. |

Exact filenames: use whatever is downloaded; do not retype from this plan. The sha is the key, not the name.

### 4.6 Fixed methodology (identical on every card)
- Context depths 4096 / 16384 / 32768 for pp512 and tg128 (llama-bench `-d` depth). KV cache f16 unless the card cannot fit it; then the cell states the KV type. Flash attention on where supported; record `-fa`.
- `-ngl 99` for models that fit; for offload rows, record `--n-cpu-moe N` and thread count `-t`.
- Same prompt/seed/threads across cards. Threads: physical cores of the host, recorded.
- A cell that OOMs or errors is a RESULT: record the exact error string, do not retry with smaller settings and report the retry as the cell.

---------------------------------------------------------------------
## 5. Correctness gate (RTX 3060 is the reference)

Run on **every** card after the speed cells, with the **same GGUF and same text**. Both parts must pass.

**5.1 Perplexity within 1% of the 3060.** Fixed text: the wikitext-2 raw test split (record its sha256 and source URL in the receipt); fixed `-c 2048 --chunks 64` (or full file if time allows), same binary commit.
```bash
# reference, on A51 R5, GPU0 (and repeat on GPU2: the two 3060s must agree with each other first)
CUDA_VISIBLE_DEVICES=0 build-cuda/bin/llama-perplexity -m <model.gguf> -f wiki.test.raw -c 2048 --chunks 64 -ngl 99 -fa on 2>&1 | tee ppl_3060_gpu0.txt
# candidate card (same flags)
build-<arch>/bin/llama-perplexity -m <model.gguf> -f wiki.test.raw -c 2048 --chunks 64 -ngl 99 -fa on 2>&1 | tee ppl_<card>.txt
```
Pass: `|ppl_card - ppl_3060| / ppl_3060 <= 0.01`. Provisional CLI: `afterlife bench --correctness --ref <3060 json>`.
Honest caveat: the same GGUF run through different CUDA/HIP/Vulkan kernels will not be bit-identical; 1% is the SPEC threshold. If a card lands at 0.5-1% it still passes but is flagged; if over 1% it is recorded as FAIL and investigated, not rerun until it passes. Where the model needs partial CPU offload the CPU path is common to all; still compare against the 3060 run with the same offload or a full-GPU 3060 run, and say which.

**5.2 Fixed answer set 3/3.** Three fixed prompts with unambiguous short answers, greedy decode (`--temp 0 --top-k 1 --seed 1`), checked by exact/regex match. The set file and its sha256 are committed in `eval/` by whoever builds it; I did not write it here. A card that gets 2/3 where the 3060 gets 3/3 fails the gate. Record raw outputs.

**A failing gate means the speed numbers for that card carry a "fast but wrong" flag in the table and are not quoted as a headline.**

---------------------------------------------------------------------
## 6. Per-card procedure (do exactly this, in order)

### 6.1 The surprise triggers (each requires a second probe before the cell is believed)
- Any tg or pp more than 25% above what the same model did on a sibling card/arch, or above the memory-bandwidth ceiling (tg tok/s x bytes-read-per-token must not exceed card bandwidth; compute it).
- Any cell much *better* than a prior unpublished lab number, or within 5% of a number we want to be true (107 tok/s, the Strata figures).
- Any stock-path "works" where the SPEC says it fails, or the reverse.
- Perplexity *lower* than the 3060 reference (suspicious, not good).
- Anything that depends on a single run.
**Second probe must differ in method**, for example: llama-bench vs `llama-server` timings field vs wall-clock (`tokens / elapsed` from a client timing a real request) vs `llama-batched-bench`. Two runs of the same command is NOT a second probe. If the two probes disagree by over 10%, the cell is `UNCONFIRMED` and stays out.

### 6.2 Stock-latest failure capture (so the "stock fails with error X" column is real)
Goal: record what a normal user would see on today's latest, verbatim. Rules: use throwaway venvs/containers under `~/afterlife-bench/<date>/stock/`, never touch the system driver, system Python, or existing ollama service; no `apt` changes; no `docker system prune` / `docker volume prune` ever (agents have wiped volumes before); remove only containers you named, by name. Save the full stdout/stderr of each, plus the exact version string and the date. Do not paraphrase the error: paste it.

**torch (NVIDIA cards B, C, E; also A as a control that it works):**
```bash
python3 -m venv stock/torch-venv && . stock/torch-venv/bin/activate
pip install --no-cache-dir torch 2>&1 | tee pip_torch.txt          # latest from PyPI default index
pip list 2>/dev/null | grep -E '^(torch|nvidia-)' | tee pip_torch_versions.txt
python -I - <<'PY' 2>&1 | tee torch_check.txt
import torch
print("torch", torch.__version__, "cuda", torch.version.cuda)
print("avail", torch.cuda.is_available())
print("cap", torch.cuda.get_device_capability(0) if torch.cuda.is_available() else None)
print("archs", torch.cuda.get_arch_list())
x = torch.zeros(1, device="cuda")      # this is where an unsupported arch raises
print("ok", x)
PY
```
Record whether `pip install` itself fails, whether the wheel installs but `get_arch_list()` lacks sm_70 / sm_61, and the exact error text from the last line. The SPEC predicts torch 2.15 dropping sm_70/sm_61; the capture decides. Also record the newest torch that still works (e.g. step down via `pip install torch==<ver> --index-url https://download.pytorch.org/whl/cu126`) to confirm the afterlife pin (2.14.0 cu126).

**vLLM (NVIDIA cards):**
```bash
python3 -m venv stock/vllm-venv && . stock/vllm-venv/bin/activate
pip install --no-cache-dir vllm 2>&1 | tee pip_vllm.txt
pip list 2>/dev/null | grep -E '^(vllm|torch) ' | tee pip_vllm_versions.txt
# smallest ungated model; any small open model works, it only needs to load
python -I -m vllm.entrypoints.openai.api_server --model <small-model-dir> --max-model-len 2048 --port 18000 2>&1 | tee vllm_serve.txt   # kill ONLY this PID after the error/ready line
```
Capture the line where it refuses the compute capability (e.g. mentions 7.0 / sm_70) or crashes in a kernel. Use a port that is free (`ss -ltn`).

**Ollama (all cards; AMD is the headline):**
```bash
# throwaway, own port and own model dir; does NOT touch the system ollama service
mkdir -p stock/ollama && cd stock/ollama
curl -fsSL https://github.com/ollama/ollama/releases/latest/download/ollama-linux-amd64.tgz -o ollama.tgz   # NVIDIA/CPU
# AMD needs the separate ROCm archive: ollama-linux-amd64-rocm.tgz ; note the exact release tag fetched
tar xzf ollama.tgz
OLLAMA_HOST=127.0.0.1:21434 OLLAMA_MODELS=$PWD/models OLLAMA_DEBUG=1 ./bin/ollama serve > serve.log 2>&1 & echo $! > ollama.pid
sleep 5; ./bin/ollama --version | tee version.txt
# load a model the card can hold (use the same 8B GGUF via a Modelfile) and watch discovery:
OLLAMA_HOST=127.0.0.1:21434 ./bin/ollama run <model> "say hi" 2>&1 | tee run.txt
grep -iE 'gfx|library=|compute=|no compatible|skipping|unsupported|filtering|inference compute' serve.log | tee gpu_discovery.txt
kill "$(cat ollama.pid)"
```
Record: does it list the GPU (`library=cuda/rocm/cpu`), or print "no compatible GPUs"/skip gfx906, and what tok/s it gets on CPU fallback (`--verbose`). For gfx906 note the version at which it stopped; memory says 0.12.3 was the last native gfx906 and SPEC says 0.13 dropped it. On .191 the system Ollama (0.12.3 and 0.32.5 variants, ollama-dual) already exists: do NOT use or restart it; use your own copy on a different port.

**Official ROCm (card D):**
```bash
# container named by us, removed by name; rocm/pytorch latest tag; record `docker inspect --format '{{.Id}} {{index .RepoDigests 0}}'`
docker run --rm --name afl-stock-rocm --device=/dev/kfd --device=/dev/dri --group-add video --security-opt seccomp=unconfined \
  -e HIP_VISIBLE_DEVICES=<gfx906 index> rocm/pytorch:latest bash -lc \
  'rocminfo | grep -E "Name:.*gfx"; python -I -c "import torch;print(torch.__version__,torch.version.hip);print(torch.cuda.is_available());print(torch.cuda.get_arch_list());print(torch.zeros(1,device=\"cuda\"))"' 2>&1 | tee rocm_stock.txt
```
Expect either "no GPU" in rocminfo or `hipErrorNoBinaryForGpu` / "invalid device function" on the first op; paste whichever occurs. Pulling a multi-GB image: confirm disk and bandwidth first. Also record the ROCm version of the tag.

**Vulkan column (AMD rows; also run on the NVIDIA rows if cheap):**
```bash
# stock llama.cpp Vulkan build, same commit, same model, same flags as HIP
cmake -B build-vk -DGGML_VULKAN=ON -DCMAKE_BUILD_TYPE=Release && cmake --build build-vk -j --target llama-bench
GGML_VK_VISIBLE_DEVICES=<gfx906 vk index> build-vk/bin/llama-bench -m <model> -p 512 -n 128 -ngl 99 -fa 1 -r 3 -o json | tee bench_vulkan.json
```
This is the honest AMD comparison: Afterlife HIP vs Vulkan, not vs nothing.

### 6.3 Afterlife bench commands (per model; same three on every card)
Provisional CLI first, then the fallback that works today. Substitute `<arch build dir>` and the three model paths. Run each model separately, 3 repeats (`-r 3`).

```bash
export CUDA_VISIBLE_DEVICES=<pinned>           # AMD: export HIP_VISIBLE_DEVICES=<pinned>
cd ~/afterlife-bench/<date>

# --- Model 1: dense ~8B (fully on GPU)
afterlife bench --model models/dense8b.gguf --ctx 4096,16384,32768 --serve 8 --power-cap-record \
    --out results/<card>_dense8b.json                         # PROVISIONAL flags
<arch build>/bin/llama-bench -m models/dense8b.gguf -p 512 -n 128 -d 0,4096,16384,32768 \
    -ngl 99 -fa 1 -r 3 -o json | tee results/<card>_dense8b_bench.json              # FALLBACK

# --- Model 2: ~26-27B (Gemma 4 26B A4B, MoE, ~4B active); on 16 GB cards state reduced ctx/offload in the cell
<arch build>/bin/llama-bench -m models/gemma4-26b-a4b.gguf -p 512 -n 128 -d 0,4096,16384,32768 \
    -ngl 99 -fa 1 -r 3 -o json | tee results/<card>_26b_bench.json
#   if OOM at a depth: that error string IS the cell. Then run an explicit offload variant as a separate, labelled row:
<arch build>/bin/llama-bench -m models/gemma4-26b-a4b.gguf -p 512 -n 128 -d 0,4096 -ngl 99 --n-cpu-moe <N> -t <cores> -r 3 -o json

# --- Model 3: 30B-class MoE with partial CPU offload (experts on CPU)
<arch build>/bin/llama-bench -m models/qwen3-30b-a3b.gguf -p 512 -n 128 -d 0,4096,16384,32768 \
    -ngl 99 --n-cpu-moe <N> -t <cores> -fa 1 -r 3 -o json | tee results/<card>_30bmoe_bench.json
#   record N, -t, host RAM free, and RAM bandwidth class; choose N once on the 3060 and keep it on every card unless the card cannot hold it (then record the N used).

# --- Serving aggregate, 8 concurrent requests (only meaningful where a server stack works)
<arch build>/bin/llama-batched-bench -m models/dense8b.gguf -c 16384 -ngl 99 -fa on \
    -npp 512 -ntg 128 -npl 8 2>&1 | tee results/<card>_dense8b_batched8.txt
# independent cross-check of the same quantity with a real server + 8 parallel clients:
<arch build>/bin/llama-server -m models/dense8b.gguf --host 127.0.0.1 --port 18080 -ngl 99 -fa on -np 8 -c 32768 &  echo $! > server.pid
# client: 8 simultaneous /completion requests of 512-token prompt, 128 tokens out, total tokens / wall time; kill "$(cat server.pid)" after
```
vLLM serving number (`vllm bench serve`, 8 concurrency) only where the stock-path capture shows vLLM runs, or on the 1Cat-vLLM SM70 wheel path once that is evaluated. Otherwise the cell is "vLLM: refuses (error string)" and serving uses llama.cpp, labelled as such.

### 6.4 Re-measurement of the two unpublished headline numbers
**~107 tok/s eGPU V100 (card C).** Currently known: Gemma 4 26B A4B QAT on the V100 via `elya-llm.service`, :8080, `v100-tame` 200 W / 1290 MHz.
1. Probe 1: `llama-bench` on the same GGUF, `-p 512 -n 128`, depth 0, pinned to the V100 UUID, service stopped, `v100-tame` active. Report tg128.
2. Probe 2 (different method): restart the model under `llama-server` standalone and time a real streamed request from the Victus over Tailscale (tokens received / generation time, from the server's `timings.predicted_per_second` AND your own wall clock). Three prompts, one of them 4k-context.
3. Probe 3 (cross-check against the ceiling): compute active-bytes-per-token x tok/s vs the card's memory bandwidth to see if 107 is plausible for ~4B active at the quant in use.
4. Only if probes 1 and 2 agree within 10% does 107 (or whatever they give) become "measured, reproduce: <cmd>". If they give a different number, the README hook is changed to the measured one. Record tg at depth 0 and at 4k/16k separately; the "107" must say its depth. State "MoE, ~4B active" beside it.
5. Repeat at the 1000 W / 800 MHz-class setting Scott OK'd for lowering the cap, only if Scott asks; not to be done silently.

**MI50 Strata numbers (card D).** Re-measure from scratch; do not quote the old ones.
1. Record link (6 above) first. 2. Probe 1: afterlife HIP llama.cpp `llama-bench` on dense8b. 3. Probe 2: Vulkan `llama-bench` same model (also fills the Vulkan column). 4. Strata, only as a documented comparison row: use the existing image `mixa3607/strata-gfx906:v0.2.9-rocm-10.1`, container name your own (`afl-strata`), mapped mode, record the exact model, quant, prompt, and tok/s as printed, with the answer-set result. If the Strata row cannot be run with a known model/prompt, it is dropped from the matrix. 5. Note which numbers are Gen1-x4-limited.

### 6.5 Power-cap settings (record for every row; change only where stated)
Power cap is a column in the result row. **Principle: do not change a limit you did not set; record what is in force.** Read everything from the tool, do not trust the defaults in this plan.
- RTX 3060 (A): record `power.limit` / `power.default_limit`. Run at default. (Reference.)
- V100 PCIe (B): record, run at default (stock V100 PCIe is nominally 250 W; verify). Optional second pass at `sudo nvidia-smi -i <idx> -pl 200` to match the eGPU's cap, then restore the recorded value. Needs sudo on .161: ask.
- V100 SXM2 eGPU (C): run **as deployed** (`v100-tame` 200 W / 1290 MHz) = the demo configuration, and name it. Do not raise the cap on the eGPU without Scott (laptop PSU/adapter and thermals). Scott's earlier OK covers lowering to 1000/800 MHz only.
- MI50 (D): `rocm-smi --showpower --showmaxpower` and `--showpoweroverdrive`; run at current. Do not change `--setpoweroverdrive` unless Scott asks; if changed, restore.
- GTX 1060 (E): record; run at default (about 120 W, verify).
Every row also gets measured average and peak draw from telem.csv, so tok/s per watt can be computed from data and not from the cap.

### 6.6 After each card
1. Stop your telemetry PID only (`kill "$(cat telem.pid)"`), remove your containers by name, delete your throwaway venvs only if disk is needed (they are evidence for the stock column; keep until the table is final).
2. Restore: services started (`systemctl is-active`), GPU_LOCK back to FREE, power limits back to the recorded values.
3. Copy results to the Victus (A51 R5, .191: password-only/ssh piping as noted), write sha256 of every result file into `eval/results/<card>/<date>/SHA256SUMS`.
4. Fill one row of `eval/CLIFF_MATRIX.csv` (to be created) with: card, host, arch, driver, toolkit, link gen/width, power cap, ctx, model sha, quant, flags, pp512, tg128, serving8, ppl, ppl_delta, answers x/3, stock-tool results (exact strings), Vulkan (AMD), reproduce command, run date, spread, flags UNCONFIRMED where applicable.
5. Run Gate G (section 1).

---------------------------------------------------------------------
## 7. tok/s per used dollar column
Needs street prices with a citation and a date for each card (eBay sold listing URL or vendor page, the date it was read). I did not look anything up and do not state prices here. Lab cost is separate: the memory records V100 32GB at about $500 and the G6 KF at $600, but those are what Scott paid, not street prices; use cited street prices as SPEC says. A cell with no cited price is left blank.

---------------------------------------------------------------------
## 8. Estimated effort and what could go wrong
- Per card: pre-flight 15 min, builds (once per arch) 20-40 min, stock-path captures 30-60 min plus downloads, bench cells (3 models x 4 depths x 3 repeats + batched + ppl) about 2-3 h. Plan one card per session; five sessions.
- Disk and RAM: .150 RAM-limited (31 GB, Wan node uses most); .187 16 GB; the 30B MoE row needs about 18 GB host RAM free.
- Biggest validity risks: eGPU link faults (Card C), Gen1 x4 (Card D), another job grabbing the GPU mid-run (re-check `nvidia-smi --query-compute-apps` after each cell), thermals on the eGPU, and a wrong device pinned (verify with a one-line `llama-bench --list-devices` or the startup log before the first cell, and confirm in the log that exactly one device was used).
- If the 1060 host never materialises, the sm_61 row ships as "proxy, untested" in the README legend; do not substitute a P40 claim.

## 9. Open questions for Scott
1. Where does a GTX 1060 live, and may it go into .187 (and may the 2070 slot/PSU be used)?
2. Which 8B dense model do you want (US-model preference vs Apache Qwen3-8B)? Gated licenses must be accepted by you.
3. Is the .191 chipset slot (Gen1 x4) fixed? May the MI50 be idle for a half day (ollama-dual, John corpus worker, 9060 XT job)?
4. OK to stop `elya-llm.service` on the G6 KF for one session?
5. May the Wan node on .150 be paused if the 30B-MoE row needs RAM (default answer: no, mark it not run)?
