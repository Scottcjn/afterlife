"""Result-row schema and (JSON/CSV) serialisation for ``afterlife bench``.

A :class:`Row` is the atomic, reproducible benchmark record. JSON is the
canonical full-fidelity form; CSV is a flattened view with a fixed column
order. Both round-trip losslessly through :func:`Row.to_dict`/:func:`Row.from_dict`
and :func:`Row.to_flat_dict`/:func:`Row.from_flat_dict`.
"""

from __future__ import annotations

import csv
import io
import json
from dataclasses import asdict, dataclass
from typing import Any

# Fixed context points the methodology measures at. Do not reorder: CSV columns
# and reproduce commands are derived from this tuple.
CONTEXT_LABELS: tuple[str, ...] = ("4k", "16k", "32k")


class SchemaError(ValueError):
    """Raised when a row or serialised payload is structurally invalid."""


@dataclass
class EnvInfo:
    """Host/accelerator environment recorded with every row."""

    driver: str
    gpu_arch: str
    power_cap_w: int | None = None


@dataclass
class PerfPoint:
    """Throughput at one context length, in tokens/second.

    ``pp512`` is prompt-processing (prefill) throughput for a 512-token prompt;
    ``tg128`` is token-generation (decode) throughput over 128 new tokens.
    """

    pp512: float
    tg128: float


@dataclass
class Methodology:
    """How the numbers were produced — captured so a row is reproducible."""

    warmup: str
    timer: str
    threads: int
    power_settings: str


@dataclass
class CorrectnessResult:
    """Outcome of the correctness gate for a row.

    The gate passes only when perplexity is within 1% of the reference AND the
    fixed question set scores a perfect ``qa_passed_count == qa_total``.
    """

    perplexity: float
    reference_perplexity: float
    perplexity_delta_pct: float
    perplexity_within_1pct: bool
    qa_total: int
    qa_passed_count: int
    qa_all_passed: bool
    passed: bool


@dataclass
class Row:
    """One reproducible benchmark result."""

    model: str
    quant: str
    backend: str
    backend_version: str
    env: EnvInfo
    perf: dict[str, PerfPoint]
    serving_8concurrent_tok_s: float | None
    correctness: CorrectnessResult
    methodology: Methodology
    reproduce_cmd: str
    timestamp: str = ""
    notes: str = ""

    # -- validation ---------------------------------------------------------
    def validate(self) -> None:
        """Raise :class:`SchemaError` if the row is structurally unusable."""
        missing = [c for c in CONTEXT_LABELS if c not in self.perf]
        if missing:
            raise SchemaError(f"perf missing context points: {missing}")
        extra = [c for c in self.perf if c not in CONTEXT_LABELS]
        if extra:
            raise SchemaError(f"perf has unknown context points: {extra}")

    def has_reproduce_cmd(self) -> bool:
        return bool(self.reproduce_cmd and self.reproduce_cmd.strip())

    # -- nested dict (JSON) -------------------------------------------------
    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Row:
        try:
            env = EnvInfo(**d["env"])
            perf = {k: PerfPoint(**v) for k, v in d["perf"].items()}
            correctness = CorrectnessResult(**d["correctness"])
            methodology = Methodology(**d["methodology"])
        except (KeyError, TypeError) as exc:
            raise SchemaError(f"cannot parse row: {exc}") from exc
        return cls(
            model=d["model"],
            quant=d["quant"],
            backend=d["backend"],
            backend_version=d["backend_version"],
            env=env,
            perf=perf,
            serving_8concurrent_tok_s=d.get("serving_8concurrent_tok_s"),
            correctness=correctness,
            methodology=methodology,
            reproduce_cmd=d["reproduce_cmd"],
            timestamp=d.get("timestamp", ""),
            notes=d.get("notes", ""),
        )

    def to_json(self, *, indent: int | None = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, sort_keys=True)

    @classmethod
    def from_json(cls, text: str) -> Row:
        return cls.from_dict(json.loads(text))

    # -- flat dict (CSV) ----------------------------------------------------
    def to_flat_dict(self) -> dict[str, str]:
        flat: dict[str, str] = {
            "model": self.model,
            "quant": self.quant,
            "backend": self.backend,
            "backend_version": self.backend_version,
            "driver": self.env.driver,
            "gpu_arch": self.env.gpu_arch,
            "power_cap_w": _opt_str(self.env.power_cap_w),
        }
        for label in CONTEXT_LABELS:
            pp = self.perf[label]
            flat[f"pp512_{label}"] = repr(pp.pp512)
            flat[f"tg128_{label}"] = repr(pp.tg128)
        flat["serving_8concurrent_tok_s"] = _opt_str(self.serving_8concurrent_tok_s)
        c = self.correctness
        flat.update(
            {
                "ppl": repr(c.perplexity),
                "ref_ppl": repr(c.reference_perplexity),
                "ppl_delta_pct": repr(c.perplexity_delta_pct),
                "ppl_within_1pct": _bool_str(c.perplexity_within_1pct),
                "qa_total": str(c.qa_total),
                "qa_passed_count": str(c.qa_passed_count),
                "qa_all_passed": _bool_str(c.qa_all_passed),
                "correctness_passed": _bool_str(c.passed),
            }
        )
        m = self.methodology
        flat.update(
            {
                "warmup": m.warmup,
                "timer": m.timer,
                "threads": str(m.threads),
                "power_settings": m.power_settings,
                "reproduce_cmd": self.reproduce_cmd,
                "timestamp": self.timestamp,
                "notes": self.notes,
            }
        )
        return flat

    @classmethod
    def flat_columns(cls) -> list[str]:
        cols = [
            "model",
            "quant",
            "backend",
            "backend_version",
            "driver",
            "gpu_arch",
            "power_cap_w",
        ]
        for label in CONTEXT_LABELS:
            cols += [f"pp512_{label}", f"tg128_{label}"]
        cols += [
            "serving_8concurrent_tok_s",
            "ppl",
            "ref_ppl",
            "ppl_delta_pct",
            "ppl_within_1pct",
            "qa_total",
            "qa_passed_count",
            "qa_all_passed",
            "correctness_passed",
            "warmup",
            "timer",
            "threads",
            "power_settings",
            "reproduce_cmd",
            "timestamp",
            "notes",
        ]
        return cols

    @classmethod
    def from_flat_dict(cls, flat: dict[str, str]) -> Row:
        try:
            env = EnvInfo(
                driver=flat["driver"],
                gpu_arch=flat["gpu_arch"],
                power_cap_w=_opt_int(flat["power_cap_w"]),
            )
            perf = {
                label: PerfPoint(
                    pp512=float(flat[f"pp512_{label}"]),
                    tg128=float(flat[f"tg128_{label}"]),
                )
                for label in CONTEXT_LABELS
            }
            correctness = CorrectnessResult(
                perplexity=float(flat["ppl"]),
                reference_perplexity=float(flat["ref_ppl"]),
                perplexity_delta_pct=float(flat["ppl_delta_pct"]),
                perplexity_within_1pct=_parse_bool(flat["ppl_within_1pct"]),
                qa_total=int(flat["qa_total"]),
                qa_passed_count=int(flat["qa_passed_count"]),
                qa_all_passed=_parse_bool(flat["qa_all_passed"]),
                passed=_parse_bool(flat["correctness_passed"]),
            )
            methodology = Methodology(
                warmup=flat["warmup"],
                timer=flat["timer"],
                threads=int(flat["threads"]),
                power_settings=flat["power_settings"],
            )
        except (KeyError, ValueError) as exc:
            raise SchemaError(f"cannot parse flat row: {exc}") from exc
        return cls(
            model=flat["model"],
            quant=flat["quant"],
            backend=flat["backend"],
            backend_version=flat["backend_version"],
            env=env,
            perf=perf,
            serving_8concurrent_tok_s=_opt_float(flat["serving_8concurrent_tok_s"]),
            correctness=correctness,
            methodology=methodology,
            reproduce_cmd=flat["reproduce_cmd"],
            timestamp=flat.get("timestamp", ""),
            notes=flat.get("notes", ""),
        )


# -- bulk (de)serialisation ------------------------------------------------
def rows_to_json(rows: list[Row], *, indent: int | None = 2) -> str:
    return json.dumps([r.to_dict() for r in rows], indent=indent, sort_keys=True)


def rows_from_json(text: str) -> list[Row]:
    data = json.loads(text)
    if not isinstance(data, list):
        raise SchemaError("expected a JSON array of rows")
    return [Row.from_dict(d) for d in data]


def rows_to_csv(rows: list[Row]) -> str:
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=Row.flat_columns())
    writer.writeheader()
    for r in rows:
        writer.writerow(r.to_flat_dict())
    return buf.getvalue()


def rows_from_csv(text: str) -> list[Row]:
    reader = csv.DictReader(io.StringIO(text))
    return [Row.from_flat_dict(dict(line)) for line in reader]


# -- helpers ---------------------------------------------------------------
def _opt_str(v: int | float | None) -> str:
    return "" if v is None else repr(v)


def _opt_int(s: str) -> int | None:
    return None if s == "" else int(s)


def _opt_float(s: str) -> float | None:
    return None if s == "" else float(s)


def _bool_str(b: bool) -> str:
    return "true" if b else "false"


def _parse_bool(s: str) -> bool:
    return s.strip().lower() in ("true", "1", "yes")
