"""Fixed inputs for the correctness gate.

These are deliberately small, original, and licence-free so the gate is fully
deterministic and shippable. They are *not* a quality benchmark; they exist only
to prove a stack produces coherent, reference-consistent output rather than
garbage. The real cliff-matrix correctness delta uses larger fixed corpora,
but the gate mechanism is identical.
"""

from __future__ import annotations

# A short, original, neutral paragraph. Perplexity is measured over this exact
# text. Keep byte-for-byte stable: changing it invalidates every reference row.
GATE_TEXT: str = (
    "A graphics card does not stop computing when its vendor stops shipping "
    "drivers. The silicon is the same today as it was the day it left the "
    "factory. What changes is the software that is willing to talk to it. "
    "This stack pins the last versions that still speak to these cards, so the "
    "hardware keeps working long after the catalog has moved on."
)

# Default reference perplexity used by ``bench selftest`` with the mock adapter.
# Real rows pass the reference measured on the RTX 3060 control card.
DEFAULT_REFERENCE_PERPLEXITY: float = 6.00

# Fixed 3-question answer set. Each question maps to the set of acceptable
# normalised answers; a model must satisfy ALL three to pass the gate.
QA_SET: tuple[tuple[str, frozenset[str]], ...] = (
    ("What is 2 + 2? Answer with a single number.", frozenset({"4", "four"})),
    ("What color is a clear daytime sky? One word.", frozenset({"blue"})),
    ("Complete the phrase: the opposite of hot is ___", frozenset({"cold"})),
)

# Canonical correct answers, used by the mock adapter's "passing" mode and by
# tests. Keyed by the exact question text.
CORRECT_ANSWERS: dict[str, str] = {
    QA_SET[0][0]: "4",
    QA_SET[1][0]: "blue",
    QA_SET[2][0]: "cold",
}

# Context points (label -> token count) the perf methodology sweeps.
CONTEXT_TOKENS: dict[str, int] = {"4k": 4096, "16k": 16384, "32k": 32768}
