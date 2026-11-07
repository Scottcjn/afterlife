# af-pkg REPORT
Built: pyproject.toml (dist name afterlife-gpu, CLI `afterlife = afterlife.cli:main`, Apache-2.0, py>=3.10, zero runtime deps, extras yaml/dev), LICENSE, NOTICE, .gitignore, DISCLAIMER.md, docs/NAME.md, models/LICENSE_RECEIPT_TEMPLATE.txt, afterlife/__init__.py (minimal, version only).
Tests: `pip install .` in fresh venv OK; import afterlife -> 0.1.0; `afterlife` script generated; ruff check clean; tomllib parses.
Not verified: running `afterlife` (afterlife/cli.py not yet written by another agent); README.md missing (pyproject references it; install tolerated it, create before publishing/sdist).
Needs Scott: confirm name afterlife-gpu; re-check availability before any publish. Nothing pushed.
