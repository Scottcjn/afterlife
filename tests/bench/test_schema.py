"""Schema validation and JSON/CSV round-trip tests."""

from __future__ import annotations

import pytest

from afterlife.bench.schema import (
    CONTEXT_LABELS,
    Row,
    SchemaError,
    rows_from_csv,
    rows_from_json,
    rows_to_csv,
    rows_to_json,
)

from .conftest import make_row


def test_validate_accepts_complete_row(valid_row: Row) -> None:
    valid_row.validate()  # must not raise


def test_validate_rejects_missing_context(valid_row: Row) -> None:
    del valid_row.perf["16k"]
    with pytest.raises(SchemaError, match="missing context"):
        valid_row.validate()


def test_validate_rejects_unknown_context(valid_row: Row) -> None:
    valid_row.perf["64k"] = valid_row.perf["4k"]
    with pytest.raises(SchemaError, match="unknown context"):
        valid_row.validate()


def test_context_labels_fixed() -> None:
    assert CONTEXT_LABELS == ("4k", "16k", "32k")


def test_json_round_trip_single(valid_row: Row) -> None:
    restored = Row.from_json(valid_row.to_json())
    assert restored == valid_row


def test_json_round_trip_bulk(valid_row: Row) -> None:
    rows = [valid_row, make_row(reproduce_cmd="cmd2", passed=False)]
    restored = rows_from_json(rows_to_json(rows))
    assert restored == rows


def test_csv_round_trip_bulk(valid_row: Row) -> None:
    rows = [valid_row, make_row(reproduce_cmd="cmd2", passed=False)]
    restored = rows_from_csv(rows_to_csv(rows))
    assert restored == rows


def test_csv_preserves_none_serving() -> None:
    row = make_row()
    row.serving_8concurrent_tok_s = None
    row.env.power_cap_w = None
    restored = rows_from_csv(rows_to_csv([row]))[0]
    assert restored.serving_8concurrent_tok_s is None
    assert restored.env.power_cap_w is None


def test_csv_columns_stable() -> None:
    cols = Row.flat_columns()
    assert cols[0] == "model"
    assert "reproduce_cmd" in cols
    for label in CONTEXT_LABELS:
        assert f"pp512_{label}" in cols
        assert f"tg128_{label}" in cols


def test_from_dict_rejects_garbage() -> None:
    with pytest.raises(SchemaError):
        Row.from_dict({"model": "x"})


def test_has_reproduce_cmd() -> None:
    assert make_row(reproduce_cmd="x").has_reproduce_cmd()
    assert not make_row(reproduce_cmd="   ").has_reproduce_cmd()
    assert not make_row(reproduce_cmd="").has_reproduce_cmd()


def test_float_fidelity_through_csv() -> None:
    row = make_row()
    row.perf["4k"].tg128 = 107.123456789
    restored = rows_from_csv(rows_to_csv([row]))[0]
    assert restored.perf["4k"].tg128 == 107.123456789
