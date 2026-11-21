"""Drift guard between migration 0004 and the ORM metadata.

Replays ``0004_plan_approvals.upgrade()`` against a recording Operations object
and asserts the tables/columns it creates match ``Base.metadata``, catching the
class of drift where a model adds a column/table the migration forgot.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

from sqlalchemy import Column
from sqlalchemy.orm import configure_mappers

from app.db.session import Base

_PATH = str(Path(__file__).resolve().parents[1] / "alembic" / "versions" / "0004_plan_approvals.py")
spec = importlib.util.spec_from_file_location("migration_0004", _PATH)
migration = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(migration)


class RecordingOps:
    """A minimal stand-in for Alembic's ``op`` that records DDL."""

    def __init__(self) -> None:
        self.tables: dict[str, set[str]] = {}
        self.indexes: set[tuple[str, str]] = set()

    def create_table(self, name: str, *columns: object, **_kw: object) -> None:
        self.tables.setdefault(name, set())
        for item in columns:
            if isinstance(item, Column):
                self.tables[name].add(item.name)

    def create_index(
        self,
        index_name: str,
        table_name: str,
        columns: list[str],
        *_a: object,
        **_kw: object,
    ) -> None:
        self.indexes.add((index_name, table_name))

    def create_foreign_key(
        self,
        constraint_name: str | None,
        table_name: str,
        referent: str,
        local_cols: list[str],
        remote_cols: list[str],
        *_a: object,
        **_kw: object,
    ) -> None:
        pass

    def drop_table(self, *_: object, **_kw: object) -> None:
        pass


def _orm_metadata() -> dict[str, set[str]]:
    configure_mappers()
    return {name: {c.name for c in table.columns} for name, table in Base.metadata.tables.items()}


def test_0004_tables_and_columns_match_orm() -> None:
    configure_mappers()
    recorded = RecordingOps()
    migration.op = recorded
    migration.upgrade()

    orm = _orm_metadata()
    for table_name, columns in recorded.tables.items():
        assert table_name in orm, f"migration creates unknown table {table_name}"
        missing = columns - orm[table_name]
        extra = orm[table_name] - columns
        assert not missing, f"{table_name}: migration missing columns {sorted(missing)}"
        assert not extra, f"{table_name}: migration has unexpected columns {sorted(extra)}"


def test_0004_creates_plan_approvals_table() -> None:
    recorded = RecordingOps()
    migration.op = recorded
    migration.upgrade()

    assert "plan_approvals" in recorded.tables
    expected = {
        "id",
        "workflow_id",
        "status",
        "plan_summary",
        "evidence_refs",
        "approver_id",
        "approver_email",
        "decision_comment",
        "decided_at",
        "requested_at",
    }
    assert recorded.tables["plan_approvals"] == expected
    recorded_indexes = {name for (name, _t) in recorded.indexes}
    assert "ix_plan_approvals_workflow_id" in recorded_indexes
    assert "ix_plan_approvals_status" in recorded_indexes
