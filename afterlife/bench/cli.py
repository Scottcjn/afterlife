"""``afterlife bench`` command-line interface.

Subcommands:

* ``run``       — produce result row(s) for a model/quant on a backend. With
                  ``--dry-run`` it prints the plan and executes nothing.
* ``selftest``  — prove the whole pipeline end-to-end against the mock backend
                  (or a tiny real CPU model) and assert the gate passes.
* ``table``     — re-emit stored rows as JSON/CSV, enforcing ``reproduce_cmd``.

The entry function is :func:`main`; the top-level ``afterlife`` dispatcher can
call ``afterlife.bench.cli:main`` with the post-``bench`` argv.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from afterlife.bench.adapter import Adapter, MockAdapter
from afterlife.bench.adapters_shell import LlamaCppAdapter, VllmAdapter
from afterlife.bench.fixtures import DEFAULT_REFERENCE_PERPLEXITY
from afterlife.bench.gate import QAOutcome
from afterlife.bench.runner import BenchJob, JobResult, format_plan, run_plan
from afterlife.bench.schema import rows_from_json
from afterlife.bench.table import TableBuilder

PROG = "afterlife bench"


def _build_adapter(args: argparse.Namespace) -> Adapter:
    if args.backend == "mock":
        # The mock passes by construction. ``--mock-ppl`` lets the demo/tests
        # drive an independent perplexity to exercise the gate's fail path.
        mock_ppl = args.mock_ppl if args.mock_ppl is not None else args.reference_ppl
        return MockAdapter(
            gpu_arch=args.gpu_arch,
            perplexity_value=mock_ppl,
            answer_mode="wrong" if args.mock_wrong else "correct",
            supports_serving=not args.no_serving,
        )
    if args.backend == "llamacpp":
        if not args.model_path:
            raise SystemExit("--model-path is required for --backend llamacpp")
        return LlamaCppAdapter(
            model_path=args.model_path,
            gpu_arch=args.gpu_arch,
            threads=args.threads,
            power_cap_w=args.power_cap_w,
            bin_dir=args.bin_dir,
        )
    if args.backend == "vllm":
        return VllmAdapter(
            model=args.model,
            gpu_arch=args.gpu_arch,
            endpoint=args.endpoint,
            power_cap_w=args.power_cap_w,
        )
    raise SystemExit(f"unknown backend: {args.backend}")


def _print_qa(outcomes: list[QAOutcome]) -> None:
    for o in outcomes:
        mark = "PASS" if o.correct else "FAIL"
        print(f"    [{mark}] Q: {o.question}\n           A: {o.model_answer!r}")


def _emit_rows(results: list[JobResult], args: argparse.Namespace) -> None:
    table = TableBuilder()
    table.extend([r.row for r in results])
    if args.json_out:
        Path(args.json_out).write_text(table.to_json(), encoding="utf-8")
        print(f"wrote {len(table)} row(s) -> {args.json_out}", file=sys.stderr)
    if args.csv_out:
        Path(args.csv_out).write_text(table.to_csv(), encoding="utf-8")
        print(f"wrote {len(table)} row(s) -> {args.csv_out}", file=sys.stderr)
    if not args.json_out and not args.csv_out:
        print(table.to_json())


def cmd_run(args: argparse.Namespace) -> int:
    adapter = _build_adapter(args)
    jobs = [
        BenchJob(
            model=args.model,
            quant=args.quant,
            reference_perplexity=args.reference_ppl,
            tolerance_pct=args.tolerance_pct,
            notes=args.notes,
        )
    ]
    if args.dry_run:
        print(format_plan(adapter, jobs))
        return 0

    results = run_plan(adapter, jobs)
    _emit_rows(results, args)
    gate = results[0].row.correctness
    status = "PASS" if gate.passed else "FAIL"
    print(
        f"correctness gate: {status} "
        f"(ppl {gate.perplexity} vs ref {gate.reference_perplexity}, "
        f"QA {gate.qa_passed_count}/{gate.qa_total})",
        file=sys.stderr,
    )
    return 0 if gate.passed else 2


def cmd_selftest(args: argparse.Namespace) -> int:
    adapter = _build_adapter(args)
    job = BenchJob(model=args.model, quant=args.quant, reference_perplexity=args.reference_ppl)
    print(f"selftest: backend={adapter.backend_name} arch={adapter.gpu_arch}")
    result = run_plan(adapter, [job])[0]
    row = result.row
    print("  perf:")
    for label, pp in row.perf.items():
        print(f"    {label:>4}: pp512={pp.pp512} tok/s  tg128={pp.tg128} tok/s")
    print(f"  serving(8): {row.serving_8concurrent_tok_s}")
    print("  correctness gate:")
    _print_qa(result.qa_outcomes)
    c = row.correctness
    print(
        f"    perplexity {c.perplexity} vs ref {c.reference_perplexity} "
        f"(delta {c.perplexity_delta_pct}%, within={c.perplexity_within_1pct})"
    )
    # Prove the table refuses a row with no reproduce_cmd, then accepts this one.
    assert row.has_reproduce_cmd(), "selftest row must carry a reproduce_cmd"
    table = TableBuilder()
    table.add(row)
    _ = rows_from_json(table.to_json())  # JSON round-trip must not raise
    ok = c.passed
    print(f"  RESULT: {'PASS — pipeline end-to-end OK' if ok else 'FAIL'}")
    return 0 if ok else 1


def cmd_table(args: argparse.Namespace) -> int:
    rows = rows_from_json(Path(args.in_path).read_text(encoding="utf-8"))
    table = TableBuilder()
    table.extend(rows)  # re-validates + enforces reproduce_cmd
    if args.csv_out:
        Path(args.csv_out).write_text(table.to_csv(), encoding="utf-8")
        print(f"wrote {len(table)} row(s) -> {args.csv_out}", file=sys.stderr)
    if args.json_out:
        Path(args.json_out).write_text(table.to_json(), encoding="utf-8")
        print(f"wrote {len(table)} row(s) -> {args.json_out}", file=sys.stderr)
    if not args.csv_out and not args.json_out:
        print(table.to_csv())
    return 0


def _add_common(p: argparse.ArgumentParser) -> None:
    p.add_argument("--backend", choices=["mock", "llamacpp", "vllm"], default="mock")
    p.add_argument("--model", default="tiny-selftest")
    p.add_argument("--quant", default="Q4_K_M")
    p.add_argument("--gpu-arch", default="sm_70")
    p.add_argument("--reference-ppl", dest="reference_ppl", type=float,
                   default=DEFAULT_REFERENCE_PERPLEXITY)
    p.add_argument("--tolerance-pct", dest="tolerance_pct", type=float, default=1.0)
    p.add_argument("--threads", type=int, default=64)
    p.add_argument("--power-cap-w", dest="power_cap_w", type=int, default=None)
    p.add_argument("--model-path", dest="model_path", default="")
    p.add_argument("--bin-dir", dest="bin_dir", default="")
    p.add_argument("--endpoint", default="http://127.0.0.1:8000")
    p.add_argument("--no-serving", dest="no_serving", action="store_true")
    p.add_argument("--notes", default="")
    # Mock-only knobs (ignored by real backends) for demos and fail-path tests.
    p.add_argument("--mock-ppl", dest="mock_ppl", type=float, default=None,
                   help="mock backend only: perplexity independent of --reference-ppl")
    p.add_argument("--mock-wrong", dest="mock_wrong", action="store_true",
                   help="mock backend only: answer the QA set incorrectly")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog=PROG, description="Afterlife fixed-methodology bench.")
    sub = parser.add_subparsers(dest="command", required=True)

    run_p = sub.add_parser("run", help="produce result row(s)")
    _add_common(run_p)
    run_p.add_argument("--dry-run", dest="dry_run", action="store_true",
                       help="print the plan; execute nothing")
    run_p.add_argument("--json", dest="json_out", default="")
    run_p.add_argument("--csv", dest="csv_out", default="")
    run_p.set_defaults(func=cmd_run)

    self_p = sub.add_parser("selftest", help="prove the pipeline end-to-end")
    _add_common(self_p)
    self_p.set_defaults(func=cmd_selftest)

    tbl_p = sub.add_parser("table", help="re-emit stored rows (enforces reproduce_cmd)")
    tbl_p.add_argument("--in", dest="in_path", required=True)
    tbl_p.add_argument("--json", dest="json_out", default="")
    tbl_p.add_argument("--csv", dest="csv_out", default="")
    tbl_p.set_defaults(func=cmd_table)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    func = args.func
    result = func(args)
    return int(result)


if __name__ == "__main__":
    sys.exit(main())
