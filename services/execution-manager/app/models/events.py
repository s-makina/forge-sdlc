"""Execution event log model.

Captures execution events, tool calls, commands, and diffs (README §12.2,
FR-5.3). Each event is attributable to an execution and carries a sequence for
ordering. Artefacts (test reports, patches) are stored in object storage and
referenced by an ``artefacts`` table keyed to the execution.
"""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models.base import TimestampMixin


class ExecutionEvent(Base, TimestampMixin):
    """A single captured execution event."""

    __tablename__ = "execution_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    execution_id: Mapped[str] = mapped_column(
        ForeignKey("executions.execution_id"), nullable=False, index=True
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    level: Mapped[str] = mapped_column(String(16), nullable=False, default="info")
    message: Mapped[str] = mapped_column(Text, nullable=False)
    details: Mapped[str | None] = mapped_column(Text)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ExecutionArtefact(Base, TimestampMixin):
    """A stored artefact (test report, patch, diff) for an execution."""

    __tablename__ = "execution_artefacts"

    id: Mapped[int] = mapped_column(primary_key=True)
    execution_id: Mapped[str] = mapped_column(
        ForeignKey("executions.execution_id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    location: Mapped[str] = mapped_column(String(1024), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    mime_type: Mapped[str | None] = mapped_column(String(128))
    kind: Mapped[str | None] = mapped_column(String(32))