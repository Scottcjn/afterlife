"""CLI end-to-end tests against the mock backend."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from afterlife.bench.cli import main
from afterlife.bench.schema import rows_from_csv, rows_from_json


def test_cli_run_mock_prints_json(capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["run", "--backend", "mock", "--model", "m", "--quant", "Q4"])
    assert rc == 0
    out = capsys.readouterr().out
    rows = rows_from_json(out)
    assert len(rows) == 1
    assert rows[0].model == "m"
    assert rows[0].correctness.passed


def test_cli_run_writes_json_and_csv(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    jf = tmp_path / "rows.json"
    cf = tmp_path / "rows.csv"
    rc = main(["run", "--model", "m", "--quant", "Q4", "--json", str(jf), "--csv", str(cf)])
    assert rc == 0
    jrows = rows_from_json(jf.read_text())
    crows = rows_from_csv(cf.read_text())
    assert jrows == crows
    assert jrows[0].has_reproduce_cmd()


def test_cli_dry_run_prints_plan(capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["run", "--dry-run", "--model", "m", "--quant", "Q4", "--gpu-arch", "gfx906"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "DRY RUN" in out
    assert "gfx906" in out
    assert "reproduce_cmd" in out


def test_cli_run_fail_path_exit_code(capsys: pytest.CaptureFixture[str]) -> None:
    # Mock perplexity far from the reference -> gate fails -> exit 2
    rc = main(["run", "--model", "m", "--quant", "Q4", "--mock-ppl", "100.0"])
    assert rc == 2


def test_cli_selftest_passes(capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["selftest"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "PASS — pipeline end-to-end OK" in out
    assert "correctness gate" in out


def test_cli_table_enforces_reproduce_cmd(tmp_path: Path) -> None:
    # Build a JSON file with one good row (via run), then corrupt reproduce_cmd.
    jf = tmp_path / "rows.json"
    main(["run", "--model", "m", "--quant", "Q4", "--json", str(jf)])
    data = json.loads(jf.read_text())
    data[0]["reproduce_cmd"] = ""
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps(data))
    with pytest.raises(Exception, match="reproduce_cmd"):
        main(["table", "--in", str(bad), "--csv", str(tmp_path / "out.csv")])


def test_cli_table_round_trip_json_to_csv(tmp_path: Path) -> None:
    jf = tmp_path / "rows.json"
    main(["run", "--model", "m", "--quant", "Q4", "--json", str(jf)])
    cf = tmp_path / "out.csv"
    rc = main(["table", "--in", str(jf), "--csv", str(cf)])
    assert rc == 0
    assert rows_from_csv(cf.read_text())[0].model == "m"
