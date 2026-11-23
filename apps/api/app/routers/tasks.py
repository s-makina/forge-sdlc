"""Task routes (Phase 4.3)."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.container import get_container
from app.db.session import get_db
from app.deps.auth import require_user
from app.models.task import Task
from app.models.user import User
from app.schemas.tasks import (
    SetDependencies,
    TaskCreate,
    TaskLaunchRead,
    TaskList,
    TaskRead,
    TaskStatusTransition,
    TaskUpdate,
)
from app.services import audit, task_launch, tasks

router = APIRouter(prefix="/tasks", tags=["tasks"])


def _get_task_or_404(db: Session, task_id: int) -> Task:
    task = tasks.get_task(db, task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return task


@router.get("", response_model=TaskList)
def list_tasks(
    project_id: int | None = None,
    status_filter: str | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_user),
) -> TaskList:
    items = tasks.list_tasks(db, project_id=project_id, status=status_filter)
    return TaskList(items=[_to_read(t) for t in items], total=len(items))


@router.post("", response_model=TaskRead, status_code=status.HTTP_201_CREATED)
def create_task(
    payload: TaskCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
) -> TaskRead:
    try:
        task = tasks.create_task(db, payload)
    except tasks.InvalidDependency as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from None
    audit.record_audit(
        db,
        action="task.create",
        entity_type="task",
        entity_id=str(task.id),
        actor_id=user.id,
        actor_email=user.email,
        details=f"Created task '{task.title}'",
    )
    return _to_read(task)


@router.get("/{task_id}", response_model=TaskRead)
def get_task(
    task_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_user),
) -> TaskRead:
    return _to_read(_get_task_or_404(db, task_id))


@router.patch("/{task_id}", response_model=TaskRead)
def update_task(
    task_id: int,
    payload: TaskUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
) -> TaskRead:
    task = _get_task_or_404(db, task_id)
    updated = tasks.update_task(db, task, payload)
    audit.record_audit(
        db,
        action="task.update",
        entity_type="task",
        entity_id=str(updated.id),
        actor_id=user.id,
        actor_email=user.email,
        details=f"Updated task '{updated.title}'",
    )
    return _to_read(updated)


@router.post("/{task_id}/status", response_model=TaskRead)
def transition_task_status(
    task_id: int,
    payload: TaskStatusTransition,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
) -> TaskRead:
    task = _get_task_or_404(db, task_id)
    try:
        updated = tasks.transition_status(db, task, payload.status, note=payload.note)
    except tasks.InvalidStatusTransition as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from None
    audit.record_audit(
        db,
        action="task.status",
        entity_type="task",
        entity_id=str(updated.id),
        actor_id=user.id,
        actor_email=user.email,
        details=f"Task '{updated.title}' -> {payload.status}",
    )
    return _to_read(updated)


@router.post("/{task_id}/dependencies", response_model=TaskRead)
def set_task_dependencies(
    task_id: int,
    payload: SetDependencies,
    db: Session = Depends(get_db),
    _: User = Depends(require_user),
) -> TaskRead:
    task = _get_task_or_404(db, task_id)
    try:
        updated = tasks.set_dependencies(db, task, payload.depends_on)
    except tasks.InvalidDependency as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from None
    return _to_read(updated)


@router.post("/{task_id}/execute", response_model=TaskLaunchRead)
def launch_task(
    task_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
) -> TaskLaunchRead:
    task = _get_task_or_404(db, task_id)
    prompt = f"{task.title}\n\n{task.description or ''}".strip()
    if task.acceptance_criteria:
        prompt = f"{prompt}\n\nAcceptance criteria:\n{task.acceptance_criteria}"
    try:
        http_client = get_container().resolve("execution_manager_client")
    except KeyError:
        http_client = None
    try:
        run_start_client = get_container().resolve("orchestrator_client")
    except KeyError:
        run_start_client = None
    try:
        result = task_launch.launch_task(
            db, task, prompt=prompt, http_client=http_client, run_start_client=run_start_client
        )
    except task_launch.NotLaunchable as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from None
    except task_launch.ExecutionManagerUnavailable as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from None
    except task_launch.LaunchError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from None
    audit.record_audit(
        db,
        action="task.launch",
        entity_type="task",
        entity_id=str(task.id),
        actor_id=user.id,
        actor_email=user.email,
        details=f"Launched task '{task.title}' as execution {result.execution_id}",
    )
    return result


def _to_read(task: Task) -> TaskRead:
    data = TaskRead.model_validate(task)
    data.dependencies = sorted(edge.depends_on_id for edge in task.dependencies_out)
    data.depends_on = sorted(edge.task_id for edge in task.dependencies_in)
    return data
