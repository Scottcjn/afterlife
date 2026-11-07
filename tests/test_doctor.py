"""End-to-end doctor tests driven by synthetic tool fixtures.

The framework probes (torch/vllm/flash_attn) import real modules, which are
absent in the test venv, so those cliffs fall back to ``stock_latest`` from the
cliff DB (torch 2.15.0, vllm 0.32.0) -- which is exactly the "what if you
install latest?" verdict we want to assert.
"""

from __future__ import annotations

import json

from afterlife.cliffs import (
    STATUS_AT_RISK,
    STATUS_BROKEN,
    STATUS_SAFE,
    STATUS_UNKNOWN,
    Finding,
    GPUReport,
    load_cliff_db,
    parse_version,
    version_ge,
)
from afterlife.detect import (
    cc_to_sm,
    detect_environment,
    parse_lspci,
    parse_nvidia_smi,
    parse_rocminfo,
)
from afterlife.doctor import render_human, render_json, run_doctor

from . import fixtures as fx


def _reports(
    outputs: dict[str, str | None],
    frameworks: dict[str, str | None] | None = None,
) -> list[GPUReport]:
    # Probe frameworks only through this explicit map, never the host venv,
    # so results do not change when torch/vllm happen to be pip-installed.
    fw = frameworks or {}
    runner = fx.make_runner(outputs)
    env = detect_environment(runner=runner, importer=lambda mod: fw.get(mod))
    _, _, reports = run_doctor(db=load_cliff_db(), env=env)
    return reports


def _finding(rep: GPUReport, cliff_id: str) -> Finding | None:
    for f in rep.findings:
        if f.cliff.id == cliff_id:
            return f
    return None


# ---------------------------------------------------------------------------
# V100 (sm_70)
# ---------------------------------------------------------------------------


def test_v100_new_driver_breaks_everything() -> None:
    reps = _reports(
        {
            "nvidia-smi": fx.NVIDIA_SMI_V100_NEW_DRIVER,
            "nvcc": fx.NVCC_13,
        }
    )
    assert len(reps) == 1
    rep = reps[0]
    assert rep.gpu.arch == "sm_70"
    assert rep.gpu.vendor == "nvidia"
    assert rep.worst_status == STATUS_BROKEN

    # CUDA 13 toolkit installed -> broken, fix pins 12.9
    cuda = _finding(rep, "cuda13_drops_pre_turing")
    assert cuda is not None and cuda.status == STATUS_BROKEN
    assert "12.9" in cuda.cliff.fix

    # Driver 590 is past the 580 branch -> broken, fix says stay on 580
    drv = _finding(rep, "r580_last_driver_branch")
    assert drv is not None and drv.status == STATUS_BROKEN
    assert "580" in drv.cliff.fix

    # torch not installed -> stock-latest 2.15.0 >= 2.15.0 cliff -> broken
    torch = _finding(rep, "torch215_drops_pre_turing_wheels")
    assert torch is not None and torch.status == STATUS_BROKEN
    assert torch.compared_is_stock and torch.compared_version == "2.15.0"
    assert "2.14.0" in torch.cliff.fix

    # vLLM not installed -> stock-latest 0.32.0 >= 0.10.0 -> broken (partial conf.)
    vllm = _finding(rep, "vllm_dropped_v100_sm70")
    assert vllm is not None and vllm.status == STATUS_BROKEN
    assert vllm.cliff.confidence == "partial"
    assert vllm.cliff.source_confirmed is False

    # FlashAttention-2 needs sm_80+ -> sm_70 affected
    fa = _finding(rep, "flashattn2_needs_sm80")
    assert fa is not None and fa.status == STATUS_BROKEN


def test_v100_on_r580_is_at_risk_not_broken_for_driver() -> None:
    reps = _reports(
        {
            "nvidia-smi": fx.NVIDIA_SMI_V100_R580,
            "nvcc": fx.NVCC_129,  # 12.9 toolkit -> safe/at-risk
        }
    )
    rep = reps[0]
    assert rep.gpu.arch == "sm_70"

    # Driver 580.173.02 is below the 590 cliff -> works now, do not upgrade
    drv = _finding(rep, "r580_last_driver_branch")
    assert drv is not None and drv.status == STATUS_AT_RISK
    assert drv.installed_version == "580.173.02"

    # CUDA 12.9 installed, below 13.0 cliff -> at-risk (last_good set)
    cuda = _finding(rep, "cuda13_drops_pre_turing")
    assert cuda is not None and cuda.status == STATUS_AT_RISK
    assert cuda.installed_version == "12.9"

    # but torch/vllm (stock-latest) still break it -> overall broken
    assert rep.worst_status == STATUS_BROKEN


def test_v100_old_driver_no_compute_cap_uses_name_map() -> None:
    reps = _reports({"nvidia-smi": fx.NVIDIA_SMI_V100_NOCC})
    assert reps[0].gpu.arch == "sm_70"  # resolved from "V100" name, not compute_cap


# ---------------------------------------------------------------------------
# GTX 1060 (sm_61) -- Pascal / P40 proxy
# ---------------------------------------------------------------------------


def test_gtx1060_pascal() -> None:
    reps = _reports({"nvidia-smi": fx.NVIDIA_SMI_GTX1060, "nvcc": fx.NVCC_13})
    rep = reps[0]
    assert rep.gpu.arch == "sm_61"
    assert rep.worst_status == STATUS_BROKEN

    cuda = _finding(rep, "cuda13_drops_pre_turing")
    assert cuda is not None and cuda.status == STATUS_BROKEN

    torch = _finding(rep, "torch215_drops_pre_turing_wheels")
    assert torch is not None and torch.status == STATUS_BROKEN

    fa = _finding(rep, "flashattn2_needs_sm80")
    assert fa is not None and fa.status == STATUS_BROKEN

    # vLLM cliff is V100/sm_70 only -> must NOT apply to sm_61
    assert _finding(rep, "vllm_dropped_v100_sm70") is None
    # AMD/ROCm cliffs must not apply to an NVIDIA card
    assert _finding(rep, "rocm7_drops_gfx906") is None


# ---------------------------------------------------------------------------
# MI50 (gfx906)
# ---------------------------------------------------------------------------


def test_mi50_gfx906() -> None:
    reps = _reports({"rocminfo": fx.ROCMINFO_MI50, "ollama": fx.OLLAMA_STOCK})
    rep = reps[0]
    assert rep.gpu.arch == "gfx906"
    assert rep.gpu.vendor == "amd"
    assert rep.worst_status == STATUS_BROKEN

    rocm7 = _finding(rep, "rocm7_drops_gfx906")
    assert rocm7 is not None and rocm7.status == STATUS_BROKEN
    assert "TheRock" in rocm7.cliff.fix or "Vulkan" in rocm7.cliff.fix

    # Ollama 0.40.15 installed (via runner) -> past 0.13.0 cliff -> broken,
    # but confidence is unverified and source_confirmed False.
    ollama = _finding(rep, "ollama013_dropped_gfx906")
    assert ollama is not None and ollama.status == STATUS_BROKEN
    assert ollama.installed_version == "0.40.15"
    assert ollama.cliff.confidence == "unverified"
    assert ollama.cliff.source_confirmed is False

    # ROCm 6.4 Tensile claim is unverified -> present but flagged
    tensile = _finding(rep, "rocm64_drops_gfx906_tensile")
    assert tensile is not None and tensile.cliff.source_confirmed is False

    # NVIDIA cliffs must not apply
    assert _finding(rep, "cuda13_drops_pre_turing") is None


def test_mi50_old_ollama_safe_for_that_cliff() -> None:
    reps = _reports({"rocminfo": fx.ROCMINFO_MI50, "ollama": fx.OLLAMA_OLD})
    rep = reps[0]
    ollama = _finding(rep, "ollama013_dropped_gfx906")
    # 0.12.3 < 0.13.0 cliff -> at-risk (works, don't upgrade), not broken
    assert ollama is not None and ollama.status == STATUS_AT_RISK


# ---------------------------------------------------------------------------
# RTX 3060 (sm_86) -- supported control
# ---------------------------------------------------------------------------


def test_rtx3060_control_is_safe() -> None:
    reps = _reports({"nvidia-smi": fx.NVIDIA_SMI_RTX3060, "nvcc": fx.NVCC_13})
    rep = reps[0]
    assert rep.gpu.arch == "sm_86"
    assert rep.worst_status == STATUS_SAFE
    assert rep.findings == []  # no cliffs apply to Ampere


# ---------------------------------------------------------------------------
# Tool absent -- must not crash
# ---------------------------------------------------------------------------


def test_all_tools_absent_no_crash() -> None:
    reps = _reports({})  # every tool missing
    assert reps == []
    # rendering must also not crash on an empty environment
    runner = fx.make_runner({})
    env, db, reports = run_doctor(runner=runner, db=load_cliff_db())
    human = render_human(env, db, reports)
    assert "No GPUs detected" in human
    assert env.tools_present["nvidia-smi"] is False
    data = json.loads(render_json(env, db, reports))
    assert data["gpus"] == []


# ---------------------------------------------------------------------------
# Unknown / brand-new GPU -- fail safe
# ---------------------------------------------------------------------------


def test_unknown_gpu_fails_safe() -> None:
    # Only lspci available, and the device name is unrecognised -> arch is None.
    reps = _reports({"lspci": fx.LSPCI_UNKNOWN_NVIDIA})
    assert len(reps) == 1
    rep = reps[0]
    assert rep.gpu.vendor == "nvidia"
    assert rep.gpu.arch is None
    assert rep.worst_status == STATUS_UNKNOWN
    assert rep.findings == []  # no guessing -> no cliffs, no crash

    runner = fx.make_runner({"lspci": fx.LSPCI_UNKNOWN_NVIDIA})
    env, db, reports = run_doctor(runner=runner, db=load_cliff_db())
    human = render_human(env, db, reports)
    assert "UNKNOWN" in human
    data = json.loads(render_json(env, db, reports))
    assert data["gpus"][0]["arch"] is None
    assert data["gpus"][0]["overall_status"] == STATUS_UNKNOWN


# ---------------------------------------------------------------------------
# Unit tests for the small pure helpers
# ---------------------------------------------------------------------------


def test_cc_to_sm() -> None:
    assert cc_to_sm("7.0") == "sm_70"
    assert cc_to_sm("8.6") == "sm_86"
    assert cc_to_sm("[Not Supported]") is None


def test_version_compare() -> None:
    assert parse_version("2.14.0+cu126") == (2, 14, 0)
    assert version_ge("2.15.0", "2.15.0")
    assert version_ge("13.0", "12.9")
    assert not version_ge("12.9", "13.0")
    assert version_ge("580.173.02", "580")  # branch compare
    assert not version_ge("580.173.02", "590")


def test_parsers_direct() -> None:
    gpus, drv = parse_nvidia_smi(fx.NVIDIA_SMI_V100_R580)
    assert drv == "580.173.02" and gpus[0].arch == "sm_70"
    assert parse_rocminfo(fx.ROCMINFO_MI50)[0].arch == "gfx906"
    assert parse_lspci(fx.LSPCI_UNKNOWN_NVIDIA)[0].arch is None


def test_yaml_json_sidecar_in_sync() -> None:
    """The stdlib JSON fallback must mirror the authored YAML source exactly."""
    import importlib
    import json
    import os

    yaml = importlib.import_module("yaml")  # dynamic: no stub dependency for mypy

    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    pkg = os.path.join(here, "afterlife")
    with open(os.path.join(pkg, "cliff_db.yaml"), encoding="utf-8") as fh:
        from_yaml = yaml.safe_load(fh)
    with open(os.path.join(pkg, "cliff_db.json"), encoding="utf-8") as fh:
        from_json = json.load(fh)
    assert from_yaml == from_json


def test_loader_json_fallback_when_no_yaml(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """load_cliff_db must work with PyYAML absent (stdlib-only runtime)."""
    import afterlife.cliffs as cliffs_mod

    monkeypatch.setattr(cliffs_mod, "_try_import_yaml", lambda: None)
    db = cliffs_mod.load_cliff_db()
    assert len(db.cliffs) == 8
    assert db.stock_latest["torch"] == "2.15.0"
