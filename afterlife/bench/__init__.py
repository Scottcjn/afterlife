"""afterlife.bench — fixed-methodology benchmark runner.

Produces one reproducible result ``Row`` per (model, quant, backend, card)
combination: performance at fixed contexts, an optional serving-aggregate
number, and a correctness-gate verdict. Rows serialise to JSON and CSV and
MUST carry a ``reproduce_cmd`` before a table will emit them.

The runner is backend-agnostic: it drives a thin :class:`Adapter` interface.
A :class:`MockAdapter` makes the whole pipeline testable on CPU with no GPU,
no model download, and no network.
"""

from afterlife.bench.schema import (
    CONTEXT_LABELS,
    CorrectnessResult,
    EnvInfo,
    Methodology,
    PerfPoint,
    Row,
)

__all__ = [
    "CONTEXT_LABELS",
    "CorrectnessResult",
    "EnvInfo",
    "Methodology",
    "PerfPoint",
    "Row",
]
