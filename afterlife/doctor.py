"""The ``afterlife doctor`` command: detect, compare, and report."""

from __future__ import annotations

import json
from typing import Any

from .cliffs import (
    STATUS_AT_RISK,
    STATUS_BROKEN,
    STATUS_INFO,
    STATUS_SAFE,
    STATUS_UNKNOWN,
    CliffDB,
    Finding,
    GPUReport,
    build_reports,
    load_cliff_db,
)
from .detect import Environment, Runner, detect_environment, real_runner

_STATUS_MARK = {
    STATUS_BROKEN: "BROKEN ",
    STATUS_AT_RISK: "AT-RISK",
    STATUS_SAFE: "SAFE   ",
    STATUS_INFO: "INFO   ",
    STATUS_UNKNOWN: "UNKNOWN",
}


def run_doctor(
    runner: Runner = real_runner,
    db: CliffDB | None = None,
    env: Environment | None = None,
) -> tuple[Environment, CliffDB, list[GPUReport]]:
    """Detect + evaluate. Returns (env, db, reports). Pure of any printing."""
    if db is None:
        db = load_cliff_db()
    if env is None:
        env = detect_environment(runner)
    reports = build_reports(env, db)
    return env, db, reports


# ---------------------------------------------------------------------------
# Human-readable rendering
# ---------------------------------------------------------------------------


def render_human(env: Environment, db: CliffDB, reports: list[GPUReport]) -> str:
    lines: list[str] = []
    lines.append("afterlife doctor")
    lines.append(f"cliff database schema {db.schema_version}, as of {db.as_of}")
    lines.append("")

    # Detected environment summary
    lines.append("Detected:")
    present = [t for t, ok in env.tools_present.items() if ok]
    absent = [t for t, ok in env.tools_present.items() if not ok]
    lines.append(f"  tools present : {', '.join(present) if present else '(none)'}")
    lines.append(f"  tools absent  : {', '.join(absent) if absent else '(none)'}")
    lines.append(f"  nvidia driver : {env.nvidia_driver or '-'}")
    lines.append(f"  cuda toolkit  : {env.cuda_toolkit or '-'}")
    lines.append(f"  rocm          : {env.rocm or '-'}")
    fw = ", ".join(f"{k}={v}" for k, v in sorted(env.frameworks.items()) if v) or "(none)"
    lines.append(f"  frameworks    : {fw}")
    lines.append("")

    if not reports:
        lines.append("No GPUs detected. (Driver tools absent, or no GPU present.)")
        return "\n".join(lines)

    for rep in reports:
        gpu = rep.gpu
        arch = gpu.arch or "unknown-arch"
        lines.append(f"GPU: {gpu.name}  [{arch}]  ({gpu.vendor}, via {gpu.source})")
        if gpu.arch is None:
            lines.append(
                "  UNKNOWN: could not resolve this GPU's architecture. Not in the "
                "cliff database -> no verdict. (New or unrecognised card; fail-safe.)"
            )
            lines.append("")
            continue
        lines.append(f"  overall: {_STATUS_MARK[rep.worst_status].strip()}")
        if not rep.findings:
            lines.append("  no known cliffs apply to this architecture (looks safe).")
            lines.append("")
            continue
        # worst findings first
        for f in sorted(rep.findings, key=lambda x: _status_rank(x.status)):
            lines.extend(_render_finding(f))
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def _status_rank(status: str) -> int:
    order = {STATUS_BROKEN: 0, STATUS_AT_RISK: 1, STATUS_INFO: 2, STATUS_SAFE: 3, STATUS_UNKNOWN: 4}
    return order.get(status, 9)


def _render_finding(f: Finding) -> list[str]:
    c = f.cliff
    conf = c.confidence.upper()
    if not c.source_confirmed:
        conf += " (UNVERIFIED SOURCE)"
    out = [f"  [{_STATUS_MARK[f.status]}] {c.title}"]
    out.append(f"      {f.detail}")
    if f.status in (STATUS_BROKEN, STATUS_AT_RISK):
        out.append(f"      breaks: {_oneline(c.breaks)}")
        out.append(f"      FIX:    {_oneline(c.fix)}")
    out.append(f"      confidence: {conf}  |  source: {c.source}")
    return out


def _oneline(text: str) -> str:
    return " ".join(text.split())


# ---------------------------------------------------------------------------
# JSON rendering
# ---------------------------------------------------------------------------


def render_json(env: Environment, db: CliffDB, reports: list[GPUReport]) -> str:
    payload: dict[str, Any] = {
        "schema_version": db.schema_version,
        "as_of": db.as_of,
        "environment": {
            "nvidia_driver": env.nvidia_driver,
            "cuda_toolkit": env.cuda_toolkit,
            "rocm": env.rocm,
            "frameworks": env.frameworks,
            "tools_present": env.tools_present,
            "stock_latest": db.stock_latest,
        },
        "gpus": [],
    }
    for rep in reports:
        gpu_obj: dict[str, Any] = {
            "name": rep.gpu.name,
            "vendor": rep.gpu.vendor,
            "arch": rep.gpu.arch,
            "detected_via": rep.gpu.source,
            "overall_status": rep.worst_status,
            "findings": [],
        }
        for f in rep.findings:
            gpu_obj["findings"].append(
                {
                    "cliff_id": f.cliff.id,
                    "title": f.cliff.title,
                    "component": f.cliff.component,
                    "status": f.status,
                    "installed_version": f.installed_version,
                    "compared_version": f.compared_version,
                    "compared_is_stock_latest": f.compared_is_stock,
                    "cliff_version": f.cliff.cliff_version,
                    "last_good_version": f.cliff.last_good_version,
                    "breaks": _oneline(f.cliff.breaks),
                    "fix": _oneline(f.cliff.fix),
                    "confidence": f.cliff.confidence,
                    "source_confirmed": f.cliff.source_confirmed,
                    "source": f.cliff.source,
                    "detail": f.detail,
                }
            )
        payload["gpus"].append(gpu_obj)
    return json.dumps(payload, indent=2)
