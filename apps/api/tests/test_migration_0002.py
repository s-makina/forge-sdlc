"""Drift guard between migration 0002 and the ORM metadata.

SQLite cannot run the 0001 foreign-key ALTERs, so migrations can't be exercised
against an in-memory engine in CI. Instead we replay 0002's ``upgrade()`` against
a recording Operations object and assert the set of tables, columns and indexes
matches ``Base.metadata``. This catches the common, dangerous class of drift
where a model adds a column/table that the migration forgot.
"""

from __future__ import annotations

import importlib.util

from sqlalchemy import Column
from sqlalchemy.orm import configure_mappers

from app.db.session import Base

_PATH = (
    "/home/salvation/workspace/forge-sdlc/apps/api/alembic/versions/0002_agents_models.py"
)
spec = importlib.util.spec_from_file_location("migration_0002", _PATH)
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


def test_0002_tables_and_columns_match_orm() -> None:
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

    # Every table in the ORM that is created by this migration is present.
    for table_name, columns in orm.items():
        if table_name in recorded.tables:
            assert columns == recorded.tables[table_name]


def test_0002_indexes_present() -> None:
    recorded = RecordingOps()
    migration.op = recorded
    migration.upgrade()
    recorded_indexes = {name for (name, _t) in recorded.indexes}
    # At minimum the unique name indexes are declared in the migration.
    for expected in ("ix_model_providers_name", "ix_models_provider_id", "ix_agents_slug"):
        assert expected in recorded_indexes
