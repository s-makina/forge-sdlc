"""Task and workflow-tracking ORM models (Phase 4).

Tasks are first-class platform records (README §11). Each task carries its
project, workflow, status lifecycle, assignment, dependencies, repo/target
branch, skills, model profile and execution limits, and points at its results/
artefact references. ``task_dependencies`` expresses ordering between tasks so
scheduling can respect unmet dependencies (README §11, FR-6.3).
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from sqlalchemy import (
    JSON,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.base import TimestampMixin


class TaskType(StrEnum):
    """Kinds of work a task can represent."""

    FEATURE = "feature"
    BUGFIX = "bugfix"
    REFACTORING = "refactoring"
    DEPENDENCY = "dependency"
    SECURITY = "security"
    PERFORMANCE = "performance"
    TESTING = "testing"
    DOCUMENTATION = "documentation"


class TaskPriority(StrEnum):
    """Priority ordering for a task."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class TaskStatus(StrEnum):
    """Lifecycle status of a task (README §11)."""

    DRAFT = "draft"
    READY = "ready"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    REVIEW = "review"
    FAILED = "failed"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class Task(Base, TimestampMixin):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id"), nullable=False, index=True
    )
    workflow_id: Mapped[int | None] = mapped_column(ForeignKey("workflows.id"), index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)

    task_type: Mapped[str] = mapped_column(
        String(32), nullable=False, server_default=TaskType.FEATURE.value, index=True
    )
    priority: Mapped[str] = mapped_column(
        String(16), nullable=False, server_default=TaskPriority.MEDIUM.value
    )
    status: Mapped[str] = mapped_column(
        String(24), nullable=False, server_default=TaskStatus.DRAFT.value, index=True
    )

    acceptance_criteria: Mapped[str | None] = mapped_column(Text)
    repository_url: Mapped[str | None] = mapped_column(String(1024))
    target_branch: Mapped[str] = mapped_column(String(255), nullable=False, server_default="main")

    assigned_role: Mapped[str | None] = mapped_column(String(128))
    assigned_agent_id: Mapped[int | None] = mapped_column(
        ForeignKey("agents.id"), index=True
    )
    skills: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    model_profile: Mapped[str | None] = mapped_column(String(64))
    relevant_files: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)

    # Execution limits (mirror the Phase 3 execution policy columns).
    cpu_limit: Mapped[float | None] = mapped_column(Float)
    memory_limit: Mapped[str | None] = mapped_column(String(32))
    disk_limit: Mapped[str | None] = mapped_column(String(32))
    timeout_seconds: Mapped[int | None] = mapped_column(Integer)
    network_policy: Mapped[str | None] = mapped_column(String(32))

    # Results / artefact references (README §11).
    result_summary: Mapped[str | None] = mapped_column(Text)
    artefact_refs: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)

    # Most recent execution attempt (Phase 3/4 link to the execution manager).
    last_execution_id: Mapped[str | None] = mapped_column(String(64), index=True)
    last_execution_status: Mapped[str | None] = mapped_column(String(32))

    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    dependencies_out: Mapped[list[TaskDependency]] = relationship(
        foreign_keys="TaskDependency.task_id",
        back_populates="task",
        cascade="all, delete-orphan",
    )
    dependencies_in: Mapped[list[TaskDependency]] = relationship(
        foreign_keys="TaskDependency.depends_on_id",
        back_populates="depends_on",
        cascade="all, delete-orphan",
    )


class TaskDependency(Base):
    """A directed dependency: ``task`` depends on ``depends_on``."""

    __tablename__ = "task_dependencies"
    __table_args__ = (
        UniqueConstraint("task_id", "depends_on_id", name="uq_task_dependencies_edge"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id"), nullable=False, index=True)
    depends_on_id: Mapped[int] = mapped_column(
        ForeignKey("tasks.id"), nullable=False, index=True
    )

    task: Mapped[Task] = relationship(
        foreign_keys=[task_id], back_populates="dependencies_out"
    )
    depends_on: Mapped[Task] = relationship(
        foreign_keys=[depends_on_id], back_populates="dependencies_in"
    )
