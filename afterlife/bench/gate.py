"""The correctness gate.

A row passes the gate only when BOTH hold:

1. **Perplexity** over a fixed text is within a tolerance (default 1%) of a
   reference row's perplexity (the RTX 3060 control card, per SPEC).
2. **A fixed question set** is answered perfectly (all N of N).

This is the "fast but broken" guard: a stack that produces garbage fails even
if it is quick. The gate is backend-agnostic — it only calls
:meth:`Adapter.perplexity` and :meth:`Adapter.answer`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from afterlife.bench.adapter import Adapter
from afterlife.bench.fixtures import DEFAULT_REFERENCE_PERPLEXITY, GATE_TEXT, QA_SET
from afterlife.bench.schema import CorrectnessResult

DEFAULT_TOLERANCE_PCT: float = 1.0

_PUNCT = re.compile(r"[^\w\s]")
_WS = re.compile(r"\s+")


class GateError(ValueError):
    """Raised when the gate cannot be evaluated (e.g. a non-positive reference)."""


def normalize(text: str) -> str:
    """Lowercase, strip punctuation, and collapse whitespace."""
    return _WS.sub(" ", _PUNCT.sub(" ", text.lower())).strip()


def answer_is_correct(answer: str, acceptable: frozenset[str]) -> bool:
    """True if any acceptable answer appears as a whole token in ``answer``."""
    tokens = set(normalize(answer).split())
    return any(normalize(a) in tokens for a in acceptable)


def perplexity_delta_pct(perplexity: float, reference: float) -> float:
    """Percentage difference of ``perplexity`` from ``reference`` (absolute)."""
    if reference <= 0:
        raise GateError(f"reference perplexity must be positive, got {reference}")
    return abs(perplexity - reference) / reference * 100.0


def within_tolerance(perplexity: float, reference: float, tolerance_pct: float) -> bool:
    """True if perplexity is within ``tolerance_pct`` of the reference."""
    return perplexity_delta_pct(perplexity, reference) <= tolerance_pct


@dataclass
class QAOutcome:
    """Per-question gate detail, kept for debugging and selftest output."""

    question: str
    model_answer: str
    acceptable: frozenset[str]
    correct: bool


def run_qa(
    adapter: Adapter,
    *,
    model: str,
    quant: str,
    qa_set: tuple[tuple[str, frozenset[str]], ...] = QA_SET,
) -> list[QAOutcome]:
    """Ask every fixed question and score each answer."""
    outcomes: list[QAOutcome] = []
    for question, acceptable in qa_set:
        reply = adapter.answer(model=model, quant=quant, question=question)
        outcomes.append(
            QAOutcome(
                question=question,
                model_answer=reply,
                acceptable=acceptable,
                correct=answer_is_correct(reply, acceptable),
            )
        )
    return outcomes


def evaluate_gate(
    adapter: Adapter,
    *,
    model: str,
    quant: str,
    reference_perplexity: float = DEFAULT_REFERENCE_PERPLEXITY,
    text: str = GATE_TEXT,
    qa_set: tuple[tuple[str, frozenset[str]], ...] = QA_SET,
    tolerance_pct: float = DEFAULT_TOLERANCE_PCT,
) -> tuple[CorrectnessResult, list[QAOutcome]]:
    """Run the full gate and build a :class:`CorrectnessResult`.

    Returns the result plus per-question outcomes (the latter for human-readable
    selftest output; only the result enters the row).
    """
    ppl = adapter.perplexity(model=model, quant=quant, text=text)
    delta = perplexity_delta_pct(ppl, reference_perplexity)
    ppl_ok = delta <= tolerance_pct

    outcomes = run_qa(adapter, model=model, quant=quant, qa_set=qa_set)
    passed_count = sum(1 for o in outcomes if o.correct)
    total = len(outcomes)
    qa_ok = passed_count == total

    result = CorrectnessResult(
        perplexity=round(ppl, 6),
        reference_perplexity=round(reference_perplexity, 6),
        perplexity_delta_pct=round(delta, 6),
        perplexity_within_1pct=ppl_ok,
        qa_total=total,
        qa_passed_count=passed_count,
        qa_all_passed=qa_ok,
        passed=ppl_ok and qa_ok,
    )
    return result, outcomes
