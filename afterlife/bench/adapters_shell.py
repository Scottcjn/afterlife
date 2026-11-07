"""Thin shell-out adapters for real inference backends (llama.cpp, vLLM).

These construct exact commands and parse their output. They are intentionally
*thin*: no GPU sweep logic lives here, and nothing runs at import time. The
command builders and output parsers are pure functions (unit-tested); actual
execution is a GPU step Scott runs, never a parallel agent (BUILD_RULES #2).

If a required binary is missing the adapter raises :class:`AdapterError` with
the exact command that failed, so a row is never fabricated.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from collections.abc import Callable, Sequence

from afterlife.bench.adapter import Adapter, AdapterError
from afterlife.bench.schema import EnvInfo, Methodology, PerfPoint

#: A runner takes an argv list and returns captured stdout. Injected for tests.
CommandRunner = Callable[[Sequence[str]], str]


def _default_runner(argv: Sequence[str]) -> str:
    exe = argv[0]
    if shutil.which(exe) is None:
        raise AdapterError(f"required binary not found on PATH: {exe!r} (cmd: {' '.join(argv)})")
    proc = subprocess.run(argv, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise AdapterError(f"command failed ({proc.returncode}): {' '.join(argv)}\n{proc.stderr}")
    return proc.stdout


# -- pure parsers ----------------------------------------------------------
def parse_perplexity(output: str) -> float:
    """Extract the final perplexity from ``llama-perplexity`` output.

    Looks for the last ``PPL = <float>`` or ``Final estimate: PPL = <float>``.
    """
    matches = re.findall(r"PPL\s*=\s*([0-9]+\.[0-9]+)", output)
    if not matches:
        raise AdapterError(f"no PPL value found in perplexity output:\n{output[-500:]}")
    return float(matches[-1])


def parse_llama_bench_tps(output: str, *, kind: str) -> float:
    """Extract tokens/s for ``kind`` ('pp' or 'tg') from ``llama-bench`` output.

    ``llama-bench`` prints rows like ``... | pp512 | 512.34 ± 1.2 |`` in its
    table. We match the test label column and the first numeric throughput.
    """
    if kind not in ("pp", "tg"):
        raise AdapterError(f"kind must be 'pp' or 'tg', got {kind!r}")
    label = "pp512" if kind == "pp" else "tg128"
    for line in output.splitlines():
        if label in line:
            nums = re.findall(r"([0-9]+\.[0-9]+)", line)
            if nums:
                return float(nums[0])
    raise AdapterError(f"no {label} throughput found in llama-bench output:\n{output[-500:]}")


def _probe_nvidia_driver(runner: CommandRunner) -> str:
    try:
        out = runner(["nvidia-smi", "--query-gpu=driver_version", "--format=csv,noheader"])
    except AdapterError:
        return "unknown"
    return out.strip().splitlines()[0].strip() if out.strip() else "unknown"


class LlamaCppAdapter(Adapter):
    """Drives llama.cpp's ``llama-bench``, ``llama-perplexity`` and ``llama-cli``."""

    backend_name = "llama.cpp"

    def __init__(
        self,
        *,
        model_path: str,
        gpu_arch: str,
        n_gpu_layers: int = 99,
        threads: int = 64,
        power_cap_w: int | None = None,
        bin_dir: str = "",
        runner: CommandRunner | None = None,
    ) -> None:
        self._model_path = model_path
        self._gpu_arch = gpu_arch
        self._ngl = n_gpu_layers
        self._threads = threads
        self._power_cap_w = power_cap_w
        self._bin = (bin_dir.rstrip("/") + "/") if bin_dir else ""
        self._runner = runner or _default_runner

    def _exe(self, name: str) -> str:
        return f"{self._bin}{name}"

    def backend_version(self) -> str:
        out = self._runner([self._exe("llama-cli"), "--version"])
        m = re.search(r"version:\s*(\S+)", out) or re.search(r"\bb?\d{3,}\b", out)
        return m.group(1) if m and m.lastindex else out.strip().splitlines()[0]

    def env_info(self) -> EnvInfo:
        return EnvInfo(
            driver=_probe_nvidia_driver(self._runner),
            gpu_arch=self._gpu_arch,
            power_cap_w=self._power_cap_w,
        )

    def methodology(self) -> Methodology:
        cap = "unlimited" if self._power_cap_w is None else f"{self._power_cap_w}W"
        return Methodology(
            warmup="llama-bench default (warmup iterations discarded)",
            timer="llama-bench internal (monotonic)",
            threads=self._threads,
            power_settings=f"power_cap={cap}; -ngl {self._ngl}; -t {self._threads}",
        )

    def _bench_argv(self, context_tokens: int) -> list[str]:
        return [
            self._exe("llama-bench"),
            "-m", self._model_path,
            "-p", "512",
            "-n", "128",
            "-c", str(context_tokens),
            "-ngl", str(self._ngl),
            "-t", str(self._threads),
        ]

    def measure_perf(self, *, model: str, quant: str, context_tokens: int) -> PerfPoint:
        out = self._runner(self._bench_argv(context_tokens))
        return PerfPoint(
            pp512=parse_llama_bench_tps(out, kind="pp"),
            tg128=parse_llama_bench_tps(out, kind="tg"),
        )

    def measure_serving(self, *, model: str, quant: str, concurrency: int) -> float | None:
        # llama.cpp's single-stream bench is not a serving-aggregate; the spec
        # reserves that column for vLLM. Report unsupported rather than fake it.
        return None

    def perplexity(self, *, model: str, quant: str, text: str) -> float:
        # Caller writes ``text`` to a file; see runner. We accept a path here.
        out = self._runner(
            [self._exe("llama-perplexity"), "-m", self._model_path, "-f", text,
             "-ngl", str(self._ngl), "-t", str(self._threads)]
        )
        return parse_perplexity(out)

    def answer(self, *, model: str, quant: str, question: str) -> str:
        out = self._runner(
            [self._exe("llama-cli"), "-m", self._model_path, "-p", question,
             "-n", "32", "--temp", "0", "-ngl", str(self._ngl), "-t", str(self._threads),
             "--no-display-prompt"]
        )
        return out.strip()

    def reproduce_cmd(self, *, model: str, quant: str) -> str:
        return " ".join(self._bench_argv(32768))


class VllmAdapter(Adapter):
    """Drives a vLLM endpoint for the serving-aggregate column.

    vLLM is the only backend the spec credits with a real 8-concurrent serving
    number. Perplexity/answer go through an OpenAI-compatible client command;
    those are wired by Scott's GPU step. Unimplemented measurement paths raise
    rather than return a placeholder.
    """

    backend_name = "vllm"

    def __init__(
        self,
        *,
        model: str,
        gpu_arch: str,
        endpoint: str = "http://127.0.0.1:8000",
        power_cap_w: int | None = None,
        threads: int = 0,
        runner: CommandRunner | None = None,
    ) -> None:
        self._model = model
        self._gpu_arch = gpu_arch
        self._endpoint = endpoint
        self._power_cap_w = power_cap_w
        self._threads = threads
        self._runner = runner or _default_runner

    def backend_version(self) -> str:
        out = self._runner(["python", "-c", "import vllm; print(vllm.__version__)"])
        return out.strip()

    def env_info(self) -> EnvInfo:
        return EnvInfo(
            driver=_probe_nvidia_driver(self._runner),
            gpu_arch=self._gpu_arch,
            power_cap_w=self._power_cap_w,
        )

    def methodology(self) -> Methodology:
        cap = "unlimited" if self._power_cap_w is None else f"{self._power_cap_w}W"
        return Methodology(
            warmup="first batch discarded",
            timer="client wall-clock + server metrics",
            threads=self._threads,
            power_settings=f"power_cap={cap}; endpoint={self._endpoint}",
        )

    def measure_perf(self, *, model: str, quant: str, context_tokens: int) -> PerfPoint:
        raise AdapterError("vLLM single-stream perf is wired in the GPU step; not run by agents")

    def measure_serving(self, *, model: str, quant: str, concurrency: int) -> float | None:
        raise AdapterError("vLLM serving benchmark is a GPU step; see BENCH_PLAN for the command")

    def perplexity(self, *, model: str, quant: str, text: str) -> float:
        raise AdapterError("vLLM perplexity is a GPU step; not run by agents")

    def answer(self, *, model: str, quant: str, question: str) -> str:
        raise AdapterError("vLLM answer is a GPU step; not run by agents")

    def reproduce_cmd(self, *, model: str, quant: str) -> str:
        return (
            "vllm bench serve --model " + self._model + " --num-prompts 8 "
            "--max-concurrency 8 --endpoint " + self._endpoint
        )
