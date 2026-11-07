"""Runner and table-builder tests, including the dry-run no-execution guarantee."""

from __future__ import annotations

import pytest

from afterlife.bench.adapter import MockAdapter
from afterlife.bench.fixtures import CONTEXT_TOKENS
from afterlife.bench.runner import BenchJob, format_plan, plan_job, run_job, run_plan
from afterlife.bench.schema import PerfPoint
from afterlife.bench.table import MissingReproduceCommand, TableBuilder

from .conftest import make_row


class ExplodingAdapter(MockAdapter):
    """Mock whose *measurement* paths raise; static metadata still works."""

    def measure_perf(self, *, model: str, quant: str, context_tokens: int) -> PerfPoint:
        raise AssertionError("measure_perf must not run during dry-run")

    def perplexity(self, *, model: str, quant: str, text: str) -> float:
        raise AssertionError("perplexity must not run during dry-run")

    def answer(self, *, model: str, quant: str, question: str) -> str:
        raise AssertionError("answer must not run during dry-run")


def test_run_job_produces_valid_row() -> None:
    result = run_job(MockAdapter(), BenchJob(model="m", quant="Q4"))
    row = result.row
    row.validate()
    assert set(row.perf) == set(CONTEXT_TOKENS)
    assert row.backend == "mock"
    assert row.has_reproduce_cmd()
    assert row.timestamp.endswith("Z")
    assert row.correctness.passed


def test_run_plan_multiple_jobs() -> None:
    jobs = [BenchJob(model="a", quant="Q4"), BenchJob(model="b", quant="Q8")]
    results = run_plan(MockAdapter(), jobs)
    assert [r.row.model for r in results] == ["a", "b"]


def test_dry_run_executes_nothing() -> None:
    adapter = ExplodingAdapter()
    job = BenchJob(model="m", quant="Q4")
    # Neither of these may touch a measurement path.
    p = plan_job(adapter, job)
    assert p["contexts"] == list(CONTEXT_TOKENS.keys())
    assert p["reproduce_cmd"]
    text = format_plan(adapter, [job])
    assert "DRY RUN" in text
    assert "nothing is executed" in text


def test_serving_unsupported_is_none() -> None:
    adapter = MockAdapter(supports_serving=False)
    result = run_job(adapter, BenchJob(model="m", quant="Q4"))
    assert result.row.serving_8concurrent_tok_s is None


def test_table_refuses_row_without_reproduce_cmd() -> None:
    table = TableBuilder()
    with pytest.raises(MissingReproduceCommand):
        table.add(make_row(reproduce_cmd=""))
    assert len(table) == 0


def test_table_accepts_good_row_and_round_trips() -> None:
    from afterlife.bench.schema import rows_from_csv, rows_from_json

    table = TableBuilder()
    table.add(make_row())
    assert len(table) == 1
    assert rows_from_json(table.to_json())[0] == make_row()
    assert rows_from_csv(table.to_csv())[0] == make_row()


def test_gate_fail_row_still_emitted_but_marked() -> None:
    # A failing gate does NOT stop the row from existing — it is recorded as failed.
    adapter = MockAdapter(perplexity_value=100.0, answer_mode="wrong")
    result = run_job(adapter, BenchJob(model="m", quant="Q4"))
    assert not result.row.correctness.passed
    TableBuilder().add(result.row)  # still a valid, reproducible row
