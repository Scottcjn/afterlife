"""Backend-agnostic adapter interface for the bench runner.

The runner never knows which engine produced a number. It drives an
:class:`Adapter`, which exposes exactly what a result row needs: environment
facts, performance points, an optional serving-aggregate number, the two
correctness-gate primitives (perplexity + question answering), the methodology
in force, and a ``reproduce_cmd`` string for the row.

:class:`MockAdapter` is a complete, deterministic, CPU-only, no-network
implementation used by the self-test and the whole test suite. Real engines
live in :mod:`afterlife.bench.adapters_shell`.
"""

from __future__ import annotations

import hashlib
from abc import ABC, abstractmethod

from afterlife.bench.fixtures import CORRECT_ANSWERS, DEFAULT_REFERENCE_PERPLEXITY
from afterlife.bench.schema import EnvInfo, Methodology, PerfPoint


class AdapterError(RuntimeError):
    """Raised when a backend cannot satisfy a measurement request."""


class Adapter(ABC):
    """A thin, measurement-only view of one inference backend."""

    #: Short stable identifier, e.g. ``"llama.cpp"``, ``"vllm"``, ``"mock"``.
    backend_name: str = "abstract"

    @abstractmethod
    def backend_version(self) -> str:
        """Return the backend's reported version string."""

    @abstractmethod
    def env_info(self) -> EnvInfo:
        """Return driver / gpu-arch / power-cap facts for the row."""

    @abstractmethod
    def methodology(self) -> Methodology:
        """Return the warmup/timer/thread/power settings in force."""

    @abstractmethod
    def measure_perf(self, *, model: str, quant: str, context_tokens: int) -> PerfPoint:
        """Measure pp512 and tg128 (tokens/s) at a given context length."""

    @abstractmethod
    def measure_serving(self, *, model: str, quant: str, concurrency: int) -> float | None:
        """Aggregate tokens/s under ``concurrency`` requests, or ``None`` if unsupported."""

    @abstractmethod
    def perplexity(self, *, model: str, quant: str, text: str) -> float:
        """Perplexity over a fixed text (lower is better)."""

    @abstractmethod
    def answer(self, *, model: str, quant: str, question: str) -> str:
        """Greedy answer to a single fixed question."""

    @abstractmethod
    def reproduce_cmd(self, *, model: str, quant: str) -> str:
        """Exact shell command a reader can run to reproduce the row."""


def _unit_hash(*parts: str) -> float:
    """Deterministic float in [0, 1) derived from the inputs (stable across runs)."""
    h = hashlib.sha256("|".join(parts).encode()).hexdigest()
    return int(h[:8], 16) / 0xFFFFFFFF


class MockAdapter(Adapter):
    """Deterministic in-process backend for self-test and unit tests.

    Produces plausible, reproducible numbers with no GPU, no model, and no
    network. Correctness behaviour is configurable so both the pass and fail
    paths of the gate can be exercised:

    * ``perplexity_value`` — the ppl the gate will compare to its reference.
    * ``answer_mode`` — ``"correct"`` returns the canonical gate answers;
      ``"wrong"`` returns deliberately wrong answers; a ``dict`` supplies
      per-question answers (missing questions answer ``""``).
    """

    backend_name = "mock"

    def __init__(
        self,
        *,
        gpu_arch: str = "sm_70",
        driver: str = "R580-mock",
        power_cap_w: int | None = 200,
        threads: int = 64,
        perplexity_value: float = DEFAULT_REFERENCE_PERPLEXITY,
        answer_mode: str | dict[str, str] = "correct",
        supports_serving: bool = True,
        version: str = "0.0.0-mock",
    ) -> None:
        self._gpu_arch = gpu_arch
        self._driver = driver
        self._power_cap_w = power_cap_w
        self._threads = threads
        self._perplexity_value = perplexity_value
        self._answer_mode = answer_mode
        self._supports_serving = supports_serving
        self._version = version

    def backend_version(self) -> str:
        return self._version

    def env_info(self) -> EnvInfo:
        return EnvInfo(
            driver=self._driver,
            gpu_arch=self._gpu_arch,
            power_cap_w=self._power_cap_w,
        )

    def methodology(self) -> Methodology:
        cap = "unlimited" if self._power_cap_w is None else f"{self._power_cap_w}W"
        return Methodology(
            warmup="1 warmup pass discarded (mock)",
            timer="wall_clock_monotonic_ns",
            threads=self._threads,
            power_settings=f"power_cap={cap}; OMP_NUM_THREADS={self._threads}",
        )

    def measure_perf(self, *, model: str, quant: str, context_tokens: int) -> PerfPoint:
        # Plausible: throughput drops as context grows; deterministic jitter.
        base_pp = 520.0
        base_tg = 110.0
        decay = 4096.0 / float(context_tokens)
        jitter = 1.0 + 0.05 * _unit_hash(model, quant, str(context_tokens))
        return PerfPoint(
            pp512=round(base_pp * decay * jitter, 3),
            tg128=round(base_tg * (0.6 + 0.4 * decay) * jitter, 3),
        )

    def measure_serving(self, *, model: str, quant: str, concurrency: int) -> float | None:
        if not self._supports_serving:
            return None
        single = self.measure_perf(model=model, quant=quant, context_tokens=4096).tg128
        # Sub-linear scaling, deterministic.
        scale = concurrency * (0.78 + 0.02 * _unit_hash(model, quant, "serving"))
        return round(single * scale, 3)

    def perplexity(self, *, model: str, quant: str, text: str) -> float:
        return self._perplexity_value

    def answer(self, *, model: str, quant: str, question: str) -> str:
        mode = self._answer_mode
        if isinstance(mode, dict):
            return mode.get(question, "")
        if mode == "correct":
            return CORRECT_ANSWERS.get(question, "")
        if mode == "wrong":
            return "definitely not the answer"
        raise AdapterError(f"unknown answer_mode: {mode!r}")

    def reproduce_cmd(self, *, model: str, quant: str) -> str:
        return (
            f"afterlife bench run --backend mock --model {model} "
            f"--quant {quant}  # deterministic, no GPU"
        )
