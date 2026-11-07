"""The fixed-methodology bench runner.

Turns a :class:`BenchJob` (one model/quant on one backend+card) into a single
reproducible :class:`Row` by sweeping the fixed context points, taking an
optional serving-aggregate number, and running the correctness gate. The
methodology (warmup/timer/threads/power) comes straight from the adapter so it
is recorded, not assumed.

``--dry-run`` is served by :func:`plan_job`, which describes what *would* run
without touching any measurement path (safe for the no-GPU rule: it reads only
static adapter metadata and the pure ``reproduce_cmd``).
"""

from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass, field

from afterlife.bench.adapter import Adapter
from afterlife.bench.fixtures import CONTEXT_TOKENS, DEFAULT_REFERENCE_PERPLEXITY
from afterlife.bench.gate import QAOutcome, evaluate_gate
from afterlife.bench.schema import PerfPoint, Row

SERVING_CONCURRENCY = 8


@dataclass
class BenchJob:
    """One unit of benchmark work: a model+quant to measure on a backend."""

    model: str
    quant: str
    reference_perplexity: float = DEFAULT_REFERENCE_PERPLEXITY
    serving_concurrency: int = SERVING_CONCURRENCY
    tolerance_pct: float = 1.0
    notes: str = ""


@dataclass
class JobResult:
    """A produced row plus the per-question gate detail (for selftest output)."""

    row: Row
    qa_outcomes: list[QAOutcome] = field(default_factory=list)


def _utc_now_iso() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def plan_job(adapter: Adapter, job: BenchJob) -> dict[str, object]:
    """Describe what a job WOULD run, without executing any measurement."""
    return {
        "backend": adapter.backend_name,
        "gpu_arch": adapter.gpu_arch,
        "model": job.model,
        "quant": job.quant,
        "contexts": list(CONTEXT_TOKENS.keys()),
        "serving_concurrency": job.serving_concurrency,
        "reference_perplexity": job.reference_perplexity,
        "tolerance_pct": job.tolerance_pct,
        "reproduce_cmd": adapter.reproduce_cmd(model=job.model, quant=job.quant),
    }


def format_plan(adapter: Adapter, jobs: list[BenchJob]) -> str:
    """Human-readable dry-run plan for the CLI."""
    lines = [f"DRY RUN — {len(jobs)} job(s); nothing is executed.", ""]
    for i, job in enumerate(jobs, 1):
        p = plan_job(adapter, job)
        lines += [
            f"[{i}] {p['backend']} / {p['gpu_arch']} :: {p['model']} ({p['quant']})",
            f"    perf sweep        : pp512+tg128 at {', '.join(CONTEXT_TOKENS)} context",
            f"    serving aggregate : {p['serving_concurrency']}-concurrent (if supported)",
            (
                f"    correctness gate  : ppl within {p['tolerance_pct']}% of "
                f"ref={p['reference_perplexity']} + 3/3 QA"
            ),
            f"    reproduce_cmd     : {p['reproduce_cmd']}",
        ]
    return "\n".join(lines)


def run_job(adapter: Adapter, job: BenchJob) -> JobResult:
    """Execute one job end-to-end and return its row.

    Measurement order is fixed: perf sweep, then serving aggregate, then the
    correctness gate. The methodology and environment are read from the adapter.
    """
    perf: dict[str, PerfPoint] = {}
    for label, tokens in CONTEXT_TOKENS.items():
        perf[label] = adapter.measure_perf(
            model=job.model, quant=job.quant, context_tokens=tokens
        )

    serving = adapter.measure_serving(
        model=job.model, quant=job.quant, concurrency=job.serving_concurrency
    )

    correctness, qa_outcomes = evaluate_gate(
        adapter,
        model=job.model,
        quant=job.quant,
        reference_perplexity=job.reference_perplexity,
        tolerance_pct=job.tolerance_pct,
    )

    row = Row(
        model=job.model,
        quant=job.quant,
        backend=adapter.backend_name,
        backend_version=adapter.backend_version(),
        env=adapter.env_info(),
        perf=perf,
        serving_8concurrent_tok_s=serving,
        correctness=correctness,
        methodology=adapter.methodology(),
        reproduce_cmd=adapter.reproduce_cmd(model=job.model, quant=job.quant),
        timestamp=_utc_now_iso(),
        notes=job.notes,
    )
    row.validate()
    return JobResult(row=row, qa_outcomes=qa_outcomes)


def run_plan(adapter: Adapter, jobs: list[BenchJob]) -> list[JobResult]:
    """Run every job against one adapter and return their results."""
    return [run_job(adapter, job) for job in jobs]
