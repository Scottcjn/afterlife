"""Adapter tests: MockAdapter behaviour and pure shell-output parsers."""

from __future__ import annotations

import pytest

from afterlife.bench.adapter import AdapterError, MockAdapter
from afterlife.bench.adapters_shell import (
    LlamaCppAdapter,
    VllmAdapter,
    parse_llama_bench_tps,
    parse_perplexity,
)
from afterlife.bench.fixtures import CONTEXT_TOKENS, CORRECT_ANSWERS, QA_SET


def test_mock_is_deterministic() -> None:
    a = MockAdapter()
    p1 = a.measure_perf(model="m", quant="Q4", context_tokens=4096)
    p2 = a.measure_perf(model="m", quant="Q4", context_tokens=4096)
    assert p1 == p2


def test_mock_perf_decays_with_context() -> None:
    a = MockAdapter()
    p4 = a.measure_perf(model="m", quant="Q4", context_tokens=CONTEXT_TOKENS["4k"])
    p32 = a.measure_perf(model="m", quant="Q4", context_tokens=CONTEXT_TOKENS["32k"])
    assert p32.pp512 < p4.pp512
    assert p32.tg128 < p4.tg128


def test_mock_serving_optional() -> None:
    assert MockAdapter(supports_serving=True).measure_serving(
        model="m", quant="Q4", concurrency=8
    ) is not None
    assert MockAdapter(supports_serving=False).measure_serving(
        model="m", quant="Q4", concurrency=8
    ) is None


def test_mock_answer_modes() -> None:
    q = QA_SET[0][0]
    assert MockAdapter(answer_mode="correct").answer(model="m", quant="Q4", question=q) == (
        CORRECT_ANSWERS[q]
    )
    assert MockAdapter(answer_mode="wrong").answer(model="m", quant="Q4", question=q) != (
        CORRECT_ANSWERS[q]
    )
    custom = MockAdapter(answer_mode={q: "42"})
    assert custom.answer(model="m", quant="Q4", question=q) == "42"
    assert custom.answer(model="m", quant="Q4", question="unknown") == ""


def test_mock_answer_bad_mode_raises() -> None:
    with pytest.raises(AdapterError):
        MockAdapter(answer_mode="nonsense").answer(model="m", quant="Q4", question="x")


def test_mock_env_and_methodology() -> None:
    a = MockAdapter(gpu_arch="gfx906", power_cap_w=None, threads=32)
    env = a.env_info()
    assert env.gpu_arch == "gfx906"
    assert env.power_cap_w is None
    meth = a.methodology()
    assert meth.threads == 32
    assert "unlimited" in meth.power_settings


def test_mock_reproduce_cmd_nonempty() -> None:
    cmd = MockAdapter().reproduce_cmd(model="m", quant="Q4")
    assert cmd.strip()


def test_parse_perplexity_takes_last() -> None:
    out = "chunk 1: PPL = 7.10\nchunk 2: PPL = 6.02\nFinal estimate: PPL = 6.00\n"
    assert parse_perplexity(out) == 6.00


def test_parse_perplexity_no_match_raises() -> None:
    with pytest.raises(AdapterError, match="no PPL"):
        parse_perplexity("nothing here")


def test_parse_llama_bench_tps() -> None:
    out = (
        "| model | test | t/s |\n"
        "| gemma | pp512 | 512.34 ± 1.20 |\n"
        "| gemma | tg128 | 107.21 ± 0.50 |\n"
    )
    assert parse_llama_bench_tps(out, kind="pp") == 512.34
    assert parse_llama_bench_tps(out, kind="tg") == 107.21


def test_parse_llama_bench_bad_kind() -> None:
    with pytest.raises(AdapterError):
        parse_llama_bench_tps("x", kind="xx")


def test_llamacpp_reproduce_cmd_and_missing_binary() -> None:
    a = LlamaCppAdapter(model_path="/models/x.gguf", gpu_arch="sm_70")
    cmd = a.reproduce_cmd(model="x", quant="Q4_K_M")
    assert "llama-bench" in cmd and "x.gguf" in cmd
    # A runner that simulates a missing binary surfaces AdapterError, not a fake row.
    def boom(argv: object) -> str:
        raise AdapterError("required binary not found on PATH: 'llama-bench'")

    a2 = LlamaCppAdapter(model_path="/x.gguf", gpu_arch="sm_70", runner=boom)
    with pytest.raises(AdapterError):
        a2.measure_perf(model="x", quant="Q4", context_tokens=4096)


def test_llamacpp_parses_injected_output() -> None:
    bench_out = "| m | pp512 | 500.0 |\n| m | tg128 | 100.0 |\n"
    a = LlamaCppAdapter(
        model_path="/x.gguf", gpu_arch="sm_70", runner=lambda argv: bench_out
    )
    pp = a.measure_perf(model="x", quant="Q4", context_tokens=4096)
    assert pp.pp512 == 500.0
    assert pp.tg128 == 100.0
    assert a.measure_serving(model="x", quant="Q4", concurrency=8) is None


def test_vllm_serving_is_gpu_step() -> None:
    a = VllmAdapter(model="gemma", gpu_arch="sm_70")
    assert "vllm bench serve" in a.reproduce_cmd(model="gemma", quant="Q4")
    with pytest.raises(AdapterError):
        a.measure_serving(model="gemma", quant="Q4", concurrency=8)
