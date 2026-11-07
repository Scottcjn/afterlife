"""Result-table builder.

Collects :class:`Row` objects and emits them as JSON or CSV. It enforces the
SPEC's hard rule: **a row with no ``reproduce_cmd`` never enters the table.**
Rows are also structurally validated (all fixed context points present).
"""

from __future__ import annotations

from afterlife.bench.schema import Row, SchemaError, rows_to_csv, rows_to_json


class MissingReproduceCommand(ValueError):
    """Raised when a row without a reproduce command is added to a table."""


class TableBuilder:
    """Accumulates validated, reproducible rows for emission."""

    def __init__(self) -> None:
        self._rows: list[Row] = []

    def add(self, row: Row) -> None:
        """Validate and append a row. Rejects rows lacking a reproduce command."""
        row.validate()
        if not row.has_reproduce_cmd():
            raise MissingReproduceCommand(
                f"row for {row.model!r}/{row.backend!r} has no reproduce_cmd; refusing to emit "
                "(SPEC: any cell without a reproduce command stays out of the table)"
            )
        self._rows.append(row)

    def extend(self, rows: list[Row]) -> None:
        for row in rows:
            self.add(row)

    @property
    def rows(self) -> list[Row]:
        return list(self._rows)

    def __len__(self) -> int:
        return len(self._rows)

    def to_json(self, *, indent: int | None = 2) -> str:
        return rows_to_json(self._rows, indent=indent)

    def to_csv(self) -> str:
        return rows_to_csv(self._rows)


__all__ = ["MissingReproduceCommand", "SchemaError", "TableBuilder"]
