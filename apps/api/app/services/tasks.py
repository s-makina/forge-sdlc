"""Task and dependency service operations (Phase 4.3).

Tasks are first-class records with a status lifecycle and dependency graph.
This module owns CRUD, dependency wiring, and the status-transition rules
(README §11, FR-6.3). Dependencies are validated for self-references and
duplicates; scheduling (4.4) reads these edges.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.task import Task, TaskDependency, TaskStatus
from app.schemas.tasks import TaskCreate, TaskUpdate


class TaskNotFound(LookupError):
    pass


class InvalidDependency(ValueError):
    pass


class InvalidStatusTransition(ValueError):
    pass


def _with_graph(db: Session, task_id: int) -> Task | None:
    stmt = (
        select(Task)
        .where(Task.id == task_id)
        .options(
            selectinload(Task.dependencies_out),
            selectinload(Task.dependencies_in),
        )
    )
    return db.scalar(stmt)


def list_tasks(db: Session, *, project_id: int | None = None, status: str | None = None) -> list[Task]:
    stmt = select(Task).options(
        selectinload(Task.dependencies_out),
        selectinload(Task.dependencies_in),
    )
    if project_id is not None:
        stmt = stmt.where(Task.project_id == project_id)
    if status is not None:
        stmt = stmt.where(Task.status == status)
    return list(db.scalars(stmt.order_by(Task.id)).all())


def get_task(db: Session, task_id: int) -> Task | None:
    return _with_graph(db, task_id)


def create_task(db: Session, payload: TaskCreate) -> Task:
    task = Task(
        project_id=payload.project_id,
        workflow_id=payload.workflow_id,
        title=payload.title,
        description=payload.description,
        task_type=payload.task_type,
        priority=payload.priority,
        status=TaskStatus.DRAFT.value,
        acceptance_criteria=payload.acceptance_criteria,
        repository_url=payload.repository_url,
        target_branch=payload.target_branch,
        assigned_role=payload.assigned_role,
        assigned_agent_id=payload.assigned_agent_id,
        skills=list(payload.skills),
        model_profile=payload.model_profile,
        relevant_files=list(payload.relevant_files),
        cpu_limit=payload.cpu_limit,
        memory_limit=payload.memory_limit,
        disk_limit=payload.disk_limit,
        timeout_seconds=payload.timeout_seconds,
        network_policy=payload.network_policy,
    )
    db.add(task)
    db.flush()
    _set_dependencies(db, task, payload.dependencies)
    db.commit()
    refreshed = _with_graph(db, task.id)
    assert refreshed is not None
    return refreshed


def update_task(db: Session, task: Task, payload: TaskUpdate) -> Task:
    updates = payload.model_dump(exclude_unset=True, exclude_none=True)
    for field, value in updates.items():
        if field in ("skills", "relevant_files", "artefact_refs") and value is not None:
            setattr(task, field, list(value))
        else:
            setattr(task, field, value)
    db.commit()
    refreshed = _with_graph(db, task.id)
    assert refreshed is not None
    return refreshed


def transition_status(db: Session, task: Task, status: str, *, note: str | None = None) -> Task:
    """Enforce the task status lifecycle and move ``task`` to ``status``.

    Guards: a task may only be started once; completed/cancelled are terminal.
    """
    if task.status in (TaskStatus.COMPLETED.value, TaskStatus.CANCELLED.value):
        raise InvalidStatusTransition(f"task is already terminal ({task.status})")
    now = datetime.now(UTC)
    if status == TaskStatus.IN_PROGRESS.value and task.started_at is None:
        task.started_at = now
    if status in (TaskStatus.COMPLETED.value, TaskStatus.FAILED.value, TaskStatus.CANCELLED.value):
        task.finished_at = now
    task.status = status
    db.commit()
    refreshed = _with_graph(db, task.id)
    assert refreshed is not None
    return refreshed


def set_dependencies(db: Session, task: Task, depends_on_ids: list[int]) -> Task:
    """Replace the task's outgoing dependency edges."""
    _set_dependencies(db, task, depends_on_ids)
    db.commit()
    refreshed = _with_graph(db, task.id)
    assert refreshed is not None
    return refreshed


def _set_dependencies(db: Session, task: Task, depends_on_ids: list[int]) -> None:
    ids = list(dict.fromkeys(depends_on_ids))
    for dep_id in ids:
        if dep_id == task.id:
            raise InvalidDependency("a task cannot depend on itself")
    # All dependencies must exist and share the task's project.
    for dep_id in ids:
        dep = db.get(Task, dep_id)
        if dep is None:
            raise InvalidDependency(f"dependency task {dep_id} does not exist")
        if dep.project_id != task.project_id:
            raise InvalidDependency("dependencies must belong to the same project")
    existing = {edge.depends_on_id for edge in task.dependencies_out}
    to_add = [i for i in ids if i not in existing]
    to_remove = [edge for edge in task.dependencies_out if edge.depends_on_id not in ids]
    for edge in to_remove:
        db.delete(edge)
    for dep_id in to_add:
        task.dependencies_out.append(TaskDependency(depends_on_id=dep_id))


def dependencies_satisfied(db: Session, task: Task) -> bool:
    """Return True when all of the task's dependencies are completed."""
    for edge in task.dependencies_out:
        dep = db.get(Task, edge.depends_on_id)
        if dep is None or dep.status != TaskStatus.COMPLETED.value:
            return False
    return True


class TaskNotLaunchable(ValueError):
    """Raised when a task cannot be launched (status, repo, or dependency)."""


def is_launchable(db: Session, task: Task) -> bool:
    """Return True when the task may be explicitly launched by a user."""
    if task.status != TaskStatus.READY.value:
        return False
    if not task.repository_url:
        return False
    return dependencies_satisfied(db, task)


def mark_launched(db: Session, task: Task, *, result_summary: str | None = None) -> Task:
    """Transition a ready task to ``in_progress`` once an execution is created."""
    if task.status != TaskStatus.READY.value:
        raise TaskNotLaunchable(f"task is not ready (status={task.status})")
    now = datetime.now(UTC)
    if task.started_at is None:
        task.started_at = now
    task.status = TaskStatus.IN_PROGRESS.value
    if result_summary:
        task.result_summary = result_summary
    db.commit()
    refreshed = _with_graph(db, task.id)
    assert refreshed is not None
    return refreshed
