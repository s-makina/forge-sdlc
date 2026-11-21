"""Execution task-record model.

Links an execution to a task and project. Following README §12.2 each workspace
carries a unique execution identifier, project/task association, and lifecycle
state. ``task_id`` is nullable until the Phase 4 ``tasks`` table exists; it is
stored here as an opaque identifier string to avoid coupling the execution
engine worker to the control-plane schema.
"""

from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models.base import TimestampMixin


class ExecutionStatus(StrEnum):
    """Execution workspace lifecycle (README §12.1)."""

    CREATED = "created"
    READY = "ready"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CLEANING = "cleaning"
    DONE = "done"
    CANCELLED = "cancelled"


class Execution(Base, TimestampMixin):
    __tablename__ = "executions"

    id: Mapped[int] = mapped_column(primary_key=True)
    execution_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)

    # Task and project association.
    project_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    task_id: Mapped[str | None] = mapped_column(String(64), index=True)
    repository_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    branch: Mapped[str] = mapped_column(String(255), nullable=False)

    # Lifecycle state.
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default=ExecutionStatus.CREATED.value, index=True
    )
    container_id: Mapped[str | None] = mapped_column(String(128))
    session_id: Mapped[str | None] = mapped_column(String(128))
    error_message: Mapped[str | None] = mapped_column(Text)

    # Workspace policies (README §12.2 / §12.3).
    image: Mapped[str] = mapped_column(String(255), nullable=False)
    cpu_limit: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    memory_limit: Mapped[str] = mapped_column(String(32), nullable=False, default="1g")
    disk_limit: Mapped[str] = mapped_column(String(32), nullable=False, default="2g")
    timeout_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=3600)
    network_policy: Mapped[str] = mapped_column(String(32), nullable=False, default="minimal")

    # Timing.
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))