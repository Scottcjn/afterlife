"""Cliff database loading, version comparison, and per-GPU verdicts."""

from __future__ import annotations

import importlib
import json
import os
import re
from dataclasses import dataclass
from types import ModuleType
from typing import Any

from .detect import GPU, Environment

_HERE = os.path.dirname(__file__)
_CLIFF_DB_PATH = os.path.join(_HERE, "cliff_db.yaml")
_CLIFF_DB_JSON_PATH = os.path.join(_HERE, "cliff_db.json")


def _try_import_yaml() -> ModuleType | None:
    """Return the PyYAML module if installed, else None.

    Imported dynamically so the package carries NO hard PyYAML dependency
    (the runtime is stdlib-only per the packaging contract) and so static
    type-checking does not require PyYAML or its stubs.
    """
    try:
        return importlib.import_module("yaml")
    except ImportError:
        return None


def _load_raw(path: str) -> dict[str, Any]:
    """Load the cliff DB from YAML if PyYAML is available, else the JSON sidecar.

    ``cliff_db.yaml`` is the authored source of truth; ``cliff_db.json`` is a
    generated mirror so ``afterlife doctor`` works with only the standard
    library installed.
    """
    yaml = _try_import_yaml()
    if yaml is not None and os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
        if isinstance(data, dict):
            return data
    with open(_CLIFF_DB_JSON_PATH, encoding="utf-8") as fh:
        loaded: dict[str, Any] = json.load(fh)
    return loaded


@dataclass
class Cliff:
    """One support-cutoff entry from the YAML database."""

    id: str
    title: str
    component: str
    affected_arch: list[str]
    cliff_version: str | None
    last_good_version: str | None
    breaks: str
    fix: str
    confidence: str
    source_confirmed: bool
    source: str
    source_note: str = ""


@dataclass
class CliffDB:
    schema_version: int
    as_of: str
    stock_latest: dict[str, str]
    cliffs: list[Cliff]


def load_cliff_db(path: str = _CLIFF_DB_PATH) -> CliffDB:
    """Load and validate the cliff database (YAML source, JSON fallback)."""
    data: dict[str, Any] = _load_raw(path)
    cliffs = [
        Cliff(
            id=c["id"],
            title=c["title"],
            component=c["component"],
            affected_arch=list(c["affected_arch"]),
            cliff_version=_as_opt_str(c.get("cliff_version")),
            last_good_version=_as_opt_str(c.get("last_good_version")),
            breaks=c["breaks"].strip(),
            fix=c["fix"].strip(),
            confidence=c["confidence"],
            source_confirmed=bool(c["source_confirmed"]),
            source=c["source"],
            source_note=str(c.get("source_note", "")).strip(),
        )
        for c in data["cliffs"]
    ]
    return CliffDB(
        schema_version=int(data["schema_version"]),
        as_of=str(data["as_of"]),
        stock_latest={str(k): str(v) for k, v in (data.get("stock_latest") or {}).items()},
        cliffs=cliffs,
    )


def _as_opt_str(v: Any) -> str | None:
    return None if v is None else str(v)


# ---------------------------------------------------------------------------
# Version comparison (no external dep; tolerant of suffixes like "+cu126")
# ---------------------------------------------------------------------------


def parse_version(v: str) -> tuple[int, ...]:
    """'2.14.0+cu126' -> (2, 14, 0). Non-numeric tails are ignored."""
    head = re.split(r"[^0-9.]", v.strip(), maxsplit=1)[0]
    parts = [p for p in head.split(".") if p != ""]
    return tuple(int(p) for p in parts) if parts else (0,)


def version_ge(a: str, b: str) -> bool:
    """True if version ``a`` >= version ``b`` (component-wise, zero-padded)."""
    ta, tb = parse_version(a), parse_version(b)
    length = max(len(ta), len(tb))
    ta = ta + (0,) * (length - len(ta))
    tb = tb + (0,) * (length - len(tb))
    return ta >= tb


# ---------------------------------------------------------------------------
# Verdicts
# ---------------------------------------------------------------------------

# Status values, worst-first for sorting/overall rollup.
STATUS_BROKEN = "BROKEN"  # installed (or stock-latest) version is past the cliff
STATUS_AT_RISK = "AT_RISK"  # installed version still works but the next bump breaks it
STATUS_SAFE = "SAFE"  # installed version is at/below the last good pin
STATUS_INFO = "INFO"  # component not installed; cliff is informational / stock-latest
STATUS_UNKNOWN = "UNKNOWN"  # GPU arch could not be resolved

_SEVERITY = {
    STATUS_BROKEN: 4,
    STATUS_UNKNOWN: 3,
    STATUS_AT_RISK: 2,
    STATUS_INFO: 1,
    STATUS_SAFE: 0,
}


@dataclass
class Finding:
    """A cliff applied to one GPU, with the computed status."""

    cliff: Cliff
    status: str
    installed_version: str | None  # version actually detected, if any
    compared_version: str | None  # the version the status was computed from
    compared_is_stock: bool  # True if we fell back to stock_latest
    detail: str


@dataclass
class GPUReport:
    gpu: GPU
    findings: list[Finding]

    @property
    def worst_status(self) -> str:
        if not self.findings:
            return STATUS_UNKNOWN if self.gpu.arch is None else STATUS_SAFE
        return max((f.status for f in self.findings), key=lambda s: _SEVERITY[s])


def _component_installed_version(env: Environment, component: str) -> str | None:
    if component == "cuda":
        return env.cuda_toolkit
    if component == "nvidia_driver":
        return env.nvidia_driver
    if component == "rocm":
        return env.rocm
    return env.frameworks.get(component)


def evaluate_gpu(gpu: GPU, db: CliffDB, env: Environment) -> GPUReport:
    """Produce all findings for a single GPU against the cliff database."""
    findings: list[Finding] = []
    if gpu.arch is None:
        # Fail safe: report the unknown, do not crash and do not guess cliffs.
        return GPUReport(gpu=gpu, findings=[])

    for cliff in db.cliffs:
        if gpu.arch not in cliff.affected_arch:
            continue
        installed = _component_installed_version(env, cliff.component)
        finding = _evaluate_cliff(cliff, installed, db)
        findings.append(finding)
    return GPUReport(gpu=gpu, findings=findings)


def _evaluate_cliff(cliff: Cliff, installed: str | None, db: CliffDB) -> Finding:
    stock = db.stock_latest.get(cliff.component)

    if installed is not None:
        if cliff.cliff_version is not None and version_ge(installed, cliff.cliff_version):
            return Finding(
                cliff=cliff,
                status=STATUS_BROKEN,
                installed_version=installed,
                compared_version=installed,
                compared_is_stock=False,
                detail=(
                    f"installed {cliff.component} {installed} is at/past the "
                    f"{cliff.cliff_version} cliff"
                ),
            )
        # installed and below the cliff -> safe now, but flag the edge
        return Finding(
            cliff=cliff,
            status=STATUS_AT_RISK if cliff.last_good_version else STATUS_SAFE,
            installed_version=installed,
            compared_version=installed,
            compared_is_stock=False,
            detail=(
                f"installed {cliff.component} {installed} still works; do NOT "
                f"upgrade to/past {cliff.cliff_version}"
            ),
        )

    # Not installed: use stock-latest to answer "what if you install latest?"
    if stock is not None and cliff.cliff_version is not None:
        status = STATUS_BROKEN if version_ge(stock, cliff.cliff_version) else STATUS_INFO
        return Finding(
            cliff=cliff,
            status=status,
            installed_version=None,
            compared_version=stock,
            compared_is_stock=True,
            detail=(
                f"{cliff.component} not installed; stock-latest {stock} "
                + ("would break this card" if status == STATUS_BROKEN else "is safe")
            ),
        )

    return Finding(
        cliff=cliff,
        status=STATUS_INFO,
        installed_version=None,
        compared_version=None,
        compared_is_stock=False,
        detail=f"{cliff.component} not installed; cliff is informational",
    )


def build_reports(env: Environment, db: CliffDB) -> list[GPUReport]:
    return [evaluate_gpu(gpu, db, env) for gpu in env.gpus]
