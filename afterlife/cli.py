"""Console entry point for Afterlife."""

from __future__ import annotations

import argparse
import sys

from . import __version__
from .cliffs import STATUS_BROKEN
from .doctor import render_human, render_json, run_doctor


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="afterlife",
        description="A working stack for abandoned datacenter GPUs.",
    )
    parser.add_argument("--version", action="version", version=f"afterlife {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    doctor = sub.add_parser(
        "doctor",
        help="detect GPUs/driver/toolkit/frameworks and report what will break + the fix",
    )
    doctor.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "doctor":
        env, db, reports = run_doctor()
        if args.json:
            print(render_json(env, db, reports))
        else:
            print(render_human(env, db, reports))
        # exit code 1 if any GPU is BROKEN, so the command is CI-usable
        any_broken = any(r.worst_status == STATUS_BROKEN for r in reports)
        return 1 if any_broken else 0

    parser.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
