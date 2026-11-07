"""Correctness-gate tests: perplexity math, QA scoring, pass/fail paths."""

from __future__ import annotations

import pytest

from afterlife.bench.adapter import MockAdapter
from afterlife.bench.fixtures import DEFAULT_REFERENCE_PERPLEXITY, QA_SET
from afterlife.bench.gate import (
    GateError,
    answer_is_correct,
    evaluate_gate,
    normalize,
    perplexity_delta_pct,
    within_tolerance,
)


def test_normalize() -> None:
    assert normalize("  The SKY, is Blue!! ") == "the sky is blue"


def test_answer_is_correct_token_match() -> None:
    _q, acceptable = QA_SET[1]  # sky -> blue
    assert answer_is_correct("The sky is blue.", acceptable)
    assert answer_is_correct("blue", acceptable)
    assert not answer_is_correct("the sky is grey", acceptable)


def test_answer_is_correct_numeric_or_word() -> None:
    _, acceptable = QA_SET[0]  # 2+2 -> {4, four}
    assert answer_is_correct("it is 4", acceptable)
    assert answer_is_correct("The answer is four.", acceptable)
    assert not answer_is_correct("the answer is five", acceptable)


def test_perplexity_delta_pct() -> None:
    assert perplexity_delta_pct(6.06, 6.00) == pytest.approx(1.0)
    assert perplexity_delta_pct(6.00, 6.00) == 0.0
    assert perplexity_delta_pct(5.94, 6.00) == pytest.approx(1.0)


def test_perplexity_delta_rejects_nonpositive_ref() -> None:
    with pytest.raises(GateError):
        perplexity_delta_pct(6.0, 0.0)


def test_within_tolerance_boundary() -> None:
    # exactly 1% is within (<=)
    assert within_tolerance(6.06, 6.00, 1.0)
    # just over 1% is not
    assert not within_tolerance(6.061, 6.00, 1.0)


def test_gate_pass_path() -> None:
    adapter = MockAdapter(
        perplexity_value=DEFAULT_REFERENCE_PERPLEXITY, answer_mode="correct"
    )
    result, outcomes = evaluate_gate(adapter, model="m", quant="Q4")
    assert result.passed
    assert result.perplexity_within_1pct
    assert result.qa_all_passed
    assert result.qa_passed_count == result.qa_total == 3
    assert all(o.correct for o in outcomes)


def test_gate_fail_on_perplexity() -> None:
    # 10% off reference -> perplexity fails, answers still correct
    adapter = MockAdapter(
        perplexity_value=DEFAULT_REFERENCE_PERPLEXITY * 1.10, answer_mode="correct"
    )
    result, _ = evaluate_gate(adapter, model="m", quant="Q4")
    assert not result.perplexity_within_1pct
    assert result.qa_all_passed
    assert not result.passed


def test_gate_fail_on_qa() -> None:
    adapter = MockAdapter(
        perplexity_value=DEFAULT_REFERENCE_PERPLEXITY, answer_mode="wrong"
    )
    result, _ = evaluate_gate(adapter, model="m", quant="Q4")
    assert result.perplexity_within_1pct
    assert not result.qa_all_passed
    assert result.qa_passed_count == 0
    assert not result.passed


def test_gate_partial_qa_fails() -> None:
    # Two right, one wrong -> not 3/3 -> fail
    answers = {QA_SET[0][0]: "4", QA_SET[1][0]: "blue", QA_SET[2][0]: "warm"}
    adapter = MockAdapter(perplexity_value=DEFAULT_REFERENCE_PERPLEXITY, answer_mode=answers)
    result, _ = evaluate_gate(adapter, model="m", quant="Q4")
    assert result.qa_passed_count == 2
    assert not result.passed


def test_gate_custom_tolerance() -> None:
    adapter = MockAdapter(perplexity_value=6.30, answer_mode="correct")  # 5% off
    result, _ = evaluate_gate(adapter, model="m", quant="Q4", tolerance_pct=10.0)
    assert result.perplexity_within_1pct  # field reflects "within configured tolerance"
    assert result.passed
