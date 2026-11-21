"""Task assignment and scheduling (Phase 4.4/4.5).

Schedules ``ready`` tasks whose dependencies are satisfied, assigns them to an
agent role, and enforces the parallel-execution rules (README §11.1, FR-6.4):
- separate Git branches per task (branch = ``task/<id>``, matching Phase 3.3);
- at most ``MAX_CONCURRENT_DEVELOPERS`` (2) concurrent developer tasks per
  project to avoid working-tree collisions.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.agent import Agent, AgentVersion
from app.models.task import Task, TaskStatus
from app.models.workflow_instance import Workflow, WorkflowStatus

# MVP concurrency limit for parallel developers (README §11.1).
MAX_CONCURRENT_DEVELOPERS = 2

# Role keyed as the parallel-development cap (seeded developer role).
DEVELOPER_ROLE = "software_engineer"


class NoSuitableAgent(LookupError):
    pass


class ParallelLimitReached(RuntimeError):
    pass


def assign_to_role(db: Session, task: Task, role: str) -> Task:
    """Assign a task to the active agent version for ``role``.

    Prefers an active agent whose ``role`` matches; the task is moved to
    ``assigned`` and its ``assigned_role`` set.
    """
    version = _active_version_for_role(db, role)
    if version is None:
        raise NoSuitableAgent(f"no active agent for role '{role}'")
    task.assigned_role = role
    task.assigned_agent_id = version.agent_id
    task.status = TaskStatus.ASSIGNED.value
    db.commit()
    db.refresh(task)
    return task


def _active_version_for_role(db: Session, role: str) -> AgentVersion | None:
    stmt = (
        select(AgentVersion)
        .join(Agent, Agent.id == AgentVersion.agent_id)
        .where(Agent.role == role, Agent.is_active.is_(True))
        .order_by(AgentVersion.id.desc())
        .limit(1)
    )
    return db.scalar(stmt)


def schedulable(db: Session, task: Task) -> bool:
    """Return True when a task is ready and all its dependencies are satisfied."""
    if task.status != TaskStatus.READY.value:
        return False
    for edge in task.dependencies_out:
        dep = db.get(Task, edge.depends_on_id)
        if dep is None or dep.status != TaskStatus.COMPLETED.value:
            return False
    return True


def schedule_ready_tasks(
    db: Session,
    *,
    project_id: int | None = None,
    max_developers: int = MAX_CONCURRENT_DEVELOPERS,
) -> list[Task]:
    """Assign and start ready tasks, respecting dependencies and concurrency.

    Returns the tasks moved to ``in_progress``. A task whose assigned role is a
    developer is only started when fewer than ``max_developers`` developers are
    already ``in_progress``/``assigned`` for the project (parallel rule).
    """
    stmt = select(Task).where(Task.status == TaskStatus.READY.value)
    if project_id is not None:
        stmt = stmt.where(Task.project_id == project_id)
    ready = list(db.scalars(stmt.order_by(Task.priority).all()))

    started: list[Task] = []
    active_dev = count_developer_tasks(db, project_id=project_id)
    for task in ready:
        if not schedulable(db, task):
            continue
        role = task.assigned_role or _infer_role(task)
        if role == DEVELOPER_ROLE:
            if active_dev >= max_developers:
                continue
            active_dev += 1
        try:
            assign_to_role(db, task, role)
        except NoSuitableAgent:
            continue
        task.status = TaskStatus.IN_PROGRESS.value
        db.commit()
        db.refresh(task)
        started.append(task)
    return started


def _infer_role(task: Task) -> str:
    """Best-effort role inference from the task type."""
    if task.task_type == "testing":
        return "qa_engineer"
    if task.task_type == "review":
        return "code_reviewer"
    return DEVELOPER_ROLE


def count_developer_tasks(db: Session, *, project_id: int | None = None) -> int:
    """Count developer tasks currently running or assigned for a project."""
    stmt = select(Task).where(
        Task.assigned_role == DEVELOPER_ROLE,
        Task.status.in_(
            [TaskStatus.IN_PROGRESS.value, TaskStatus.ASSIGNED.value, TaskStatus.REVIEW.value]
        ),
    )
    if project_id is not None:
        stmt = stmt.where(Task.project_id == project_id)
    return len(list(db.scalars(stmt).all()))


def start_workflow(db: Session, workflow: Workflow) -> Workflow:
    """Mark a workflow running and schedule any of its ready tasks."""
    workflow.status = WorkflowStatus.RUNNING.value
    db.commit()
    schedule_ready_tasks(db, project_id=workflow.project_id)
    db.refresh(workflow)
    return workflow