"""Shared fixtures for bench tests."""

from __future__ import annotations

import pytest

from afterlife.bench.schema import (
    CorrectnessResult,
    EnvInfo,
    Methodology,
    PerfPoint,
    Row,
)


def make_row(*, reproduce_cmd: str = "afterlife bench run --mock", passed: bool = True) -> Row:
    """Build a fully-populated, valid :class:`Row` for tests."""
    return Row(
        model="gemma-4-26b-a4b",
        quant="Q4_K_M",
        backend="mock",
        backend_version="0.0.0-mock",
        env=EnvInfo(driver="R580", gpu_arch="sm_70", power_cap_w=200),
        perf={
            "4k": PerfPoint(pp512=512.5, tg128=107.2),
            "16k": PerfPoint(pp512=480.0, tg128=95.1),
            "32k": PerfPoint(pp512=410.3, tg128=80.4),
        },
        serving_8concurrent_tok_s=640.0,
        correctness=CorrectnessResult(
            perplexity=6.05,
            reference_perplexity=6.00,
            perplexity_delta_pct=0.833,
            perplexity_within_1pct=True,
            qa_total=3,
            qa_passed_count=3,
            qa_all_passed=True,
            passed=passed,
        ),
        methodology=Methodology(
            warmup="1 warmup pass discarded",
            timer="wall_clock_monotonic_ns",
            threads=64,
            power_settings="power_cap=200W; OMP_NUM_THREADS=64; OMP_PROC_BIND=spread",
        ),
        reproduce_cmd=reproduce_cmd,
        timestamp="2026-11-06T00:00:00Z",
        notes="synthetic test row",
    )


@pytest.fixture
def valid_row() -> Row:
    return make_row()
