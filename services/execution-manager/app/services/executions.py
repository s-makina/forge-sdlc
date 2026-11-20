"""Execution service operations.

Owns the task-record lifecycle state machine (README §12.1):
created -> ready -> running -> succeeded | failed -> cleaning -> done.

Workspace provisioning (Docker), cloning, policies, logs and artefacts are
implemented in later subphases of Phase 3; this module records state so the
lifecycle is observable and testable.
"""

from __future__ import annotations

import secrets
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.models.execution import Execution, ExecutionStatus
from app.schemas.execution import ExecutionCreate


def new_execution_id() -> str:
    """Return a unique, URL-safe execution identifier."""
    return secrets.token_urlsafe(12)


def _apply_policies(execution: Execution, payload: ExecutionCreate, settings: Settings) -> None:
    execution.image = payload.image or settings.workspace_image
    execution.cpu_limit = payload.cpu_limit or settings.workspace_cpu_limit
    execution.memory_limit = payload.memory_limit or settings.workspace_memory_limit
    execution.disk_limit = payload.disk_limit or settings.workspace_disk_limit
    execution.timeout_seconds = payload.timeout_seconds or settings.workspace_timeout_seconds
    execution.network_policy = payload.network_policy or settings.workspace_network_policy


def create_execution(db: Session, payload: ExecutionCreate) -> Execution:
    settings = get_settings()
    execution = Execution(
        execution_id=new_execution_id(),
        project_id=payload.project_id,
        task_id=payload.task_id,
        repository_url=payload.repository_url,
        branch=payload.branch,
        status=ExecutionStatus.CREATED.value,
    )
    _apply_policies(execution, payload, settings)
    db.add(execution)
    db.commit()
    db.refresh(execution)
    return execution


def get_execution(db: Session, execution_id: str) -> Execution | None:
    return db.scalar(select(Execution).where(Execution.execution_id == execution_id))


def list_executions(db: Session, *, project_id: int | None = None, limit: int = 100) -> list[Execution]:
    stmt = select(Execution).order_by(Execution.created_at.desc()).limit(limit)
    if project_id is not None:
        stmt = stmt.where(Execution.project_id == project_id)
    return list(db.scalars(stmt).all())


def transition(db: Session, execution: Execution, status: ExecutionStatus) -> Execution:
    """Move an execution to ``status``, recording start/finish timestamps."""
    execution.status = status.value
    now = datetime.now(timezone.utc)
    if status is ExecutionStatus.RUNNING and execution.started_at is None:
        execution.started_at = now
    if status in (ExecutionStatus.SUCCEEDED, ExecutionStatus.FAILED, ExecutionStatus.CANCELLED):
        execution.finished_at = now
    db.commit()
    db.refresh(execution)
    return execution


def count_active_executions(db: Session) -> int:
    """Number of executions not yet in a terminal state."""
    active = (
        ExecutionStatus.READY,
        ExecutionStatus.RUNNING,
        ExecutionStatus.CLEANING,
    )
    return db.scalar(
        select(func.count())
        .select_from(Execution)
        .where(Execution.status.in_([s.value for s in active]))
    ) or 0