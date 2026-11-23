"""Drift guard between migration 0003 and the ORM metadata.

Replays ``0003_workflows_tasks.upgrade()`` against a recording Operations object
and asserts the tables/columns it creates match ``Base.metadata``, catching the
class of drift where a model adds a column/table the migration forgot.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

from sqlalchemy import Column
from sqlalchemy.orm import configure_mappers

from app.db.session import Base

# Columns added to the ORM by migrations after 0003 (0004 plan_approvals is a
# separate table; 0005 adds provider credentials + task execution link columns).
_LATER_MIGRATION_COLUMNS = {
    "tasks": {"last_execution_id", "last_execution_status"},
}

_PATH = str(Path(__file__).resolve().parents[1] / "alembic" / "versions" / "0003_workflows_tasks.py")
spec = importlib.util.spec_from_file_location("migration_0003", _PATH)
migration = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(migration)


class RecordingOps:
    """A minimal stand-in for Alembic's ``op`` that records DDL."""

    def __init__(self) -> None:
        self.tables: dict[str, set[str]] = {}
        self.indexes: set[tuple[str, str]] = set()
        self.constraints: list[str] = []

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
        self.constraints.append(f"{table_name}.{referent}")

    def drop_table(self, *_: object, **_kw: object) -> None:
        pass


def _orm_metadata() -> dict[str, set[str]]:
    configure_mappers()
    return {name: {c.name for c in table.columns} for name, table in Base.metadata.tables.items()}


def test_0003_tables_and_columns_match_orm() -> None:
    configure_mappers()
    recorded = RecordingOps()
    migration.op = recorded
    migration.upgrade()

    orm = _orm_metadata()
    for table_name, columns in recorded.tables.items():
        assert table_name in orm, f"migration creates unknown table {table_name}"
        missing = columns - orm[table_name]
        # Columns owned by later migrations (0004/0005) are not part of 0003.
        extra = orm[table_name] - columns - _LATER_MIGRATION_COLUMNS.get(table_name, set())
        assert not missing, f"{table_name}: migration missing columns {sorted(missing)}"
        assert not extra, f"{table_name}: migration has unexpected columns {sorted(extra)}"

    for table_name, columns in orm.items():
        if table_name in recorded.tables:
            assert columns - recorded.tables[table_name] <= _LATER_MIGRATION_COLUMNS.get(
                table_name, set()
            )


def test_0003_creates_workflow_and_task_tables() -> None:
    recorded = RecordingOps()
    migration.op = recorded
    migration.upgrade()

    for table in ("workflow_templates", "workflow_stages", "workflows", "workflow_stage_runs", "tasks", "task_dependencies"):
        assert table in recorded.tables

    recorded_indexes = {name for (name, _t) in recorded.indexes}
    for expected in ("ix_workflow_templates_slug", "ix_tasks_project_id", "ix_task_dependencies_task_id"):
        assert expected in recorded_indexes
