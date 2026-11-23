"""Execution API routes.

Exposes the Phase 3.1 API surface plus the Phase 3.2 workspace-lifecycle
endpoints: request execution, poll status, fetch logs/artefacts, cancel, and
cleanup, plus provisioning a workspace container.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.deps.container import get_coding_runtime, get_docker_client
from app.docker.client import DockerClient
from app.models.execution import Execution, ExecutionStatus
from app.openhands.client import CodingRuntime
from app.schemas.execution import (
    ExecutionArtefact,
    ExecutionArtefactsRead,
    ExecutionCancelRead,
    ExecutionCleanupRead,
    ExecutionCreate,
    ExecutionList,
    ExecutionLogEntry,
    ExecutionLogsRead,
    ExecutionRead,
    ExecutionStatusRead,
    RunTaskRequest,
    RunTaskResponse,
)
from app.services import events, executions, executor, repository, runtime, terminal, workspace

router = APIRouter(prefix="/executions", tags=["executions"])


def _get_execution_or_404(db: Session, execution_id: str) -> Execution:
    execution = executions.get_execution(db, execution_id)
    if execution is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Execution not found")
    return execution


@router.post("", response_model=ExecutionRead, status_code=status.HTTP_201_CREATED)
def request_execution(payload: ExecutionCreate, db: Session = Depends(get_db)) -> ExecutionRead:
    execution = executions.create_execution(db, payload)
    return ExecutionRead.model_validate(execution)


@router.post("/{execution_id}/provision", response_model=ExecutionRead)
def provision_execution(
    execution_id: str,
    db: Session = Depends(get_db),
    docker: DockerClient = Depends(get_docker_client),
) -> ExecutionRead:
    execution = _get_execution_or_404(db, execution_id)
    execution = executor.provision(db, execution, docker, get_settings())
    return ExecutionRead.model_validate(execution)


@router.post("/{execution_id}/prepare", response_model=ExecutionRead)
def prepare_execution(
    execution_id: str,
    db: Session = Depends(get_db),
    docker: DockerClient = Depends(get_docker_client),
) -> ExecutionRead:
    execution = _get_execution_or_404(db, execution_id)
    execution = repository.prepare_repository(db, docker, execution)
    return ExecutionRead.model_validate(execution)


@router.post("/{execution_id}/start-session", response_model=ExecutionRead)
def start_session(
    execution_id: str,
    db: Session = Depends(get_db),
    coding_runtime: CodingRuntime = Depends(get_coding_runtime),
) -> ExecutionRead:
    execution = _get_execution_or_404(db, execution_id)
    _, execution = runtime.start_coding_session(db, coding_runtime, execution)
    return ExecutionRead.model_validate(execution)


@router.post("/{execution_id}/run", response_model=RunTaskResponse)
def run_task(
    execution_id: str,
    payload: RunTaskRequest,
    db: Session = Depends(get_db),
    coding_runtime: CodingRuntime = Depends(get_coding_runtime),
) -> RunTaskResponse:
    execution = _get_execution_or_404(db, execution_id)
    if not execution.session_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No coding session has been started for this execution",
        )
    result = runtime.run_task(coding_runtime, execution.session_id, payload.prompt)
    events.record_event(
        db,
        execution_id,
        kind="run_task",
        message=payload.prompt,
        level="debug",
        details="error" if not result.ok else "ok",
    )
    if not result.ok:
        workspace.fail_execution(
            db, execution, result.error or "agent task failed"
        )
    return RunTaskResponse(
        execution_id=execution_id,
        ok=result.ok,
        output=result.output,
        error=result.error,
    )


@router.post("/{execution_id}/test", response_model=ExecutionRead)
def run_test_suite(
    execution_id: str,
    db: Session = Depends(get_db),
    docker: DockerClient = Depends(get_docker_client),
) -> ExecutionRead:
    execution = _get_execution_or_404(db, execution_id)
    _, execution = terminal.run_tests(db, docker, execution)
    return ExecutionRead.model_validate(execution)


@router.get("", response_model=ExecutionList)
def list_executions(
    project_id: int | None = None, db: Session = Depends(get_db)
) -> ExecutionList:
    items = executions.list_executions(db, project_id=project_id)
    return ExecutionList(items=[ExecutionRead.model_validate(e) for e in items], total=len(items))


@router.get("/{execution_id}", response_model=ExecutionRead)
def get_execution(execution_id: str, db: Session = Depends(get_db)) -> ExecutionRead:
    return ExecutionRead.model_validate(_get_execution_or_404(db, execution_id))


@router.get("/{execution_id}/status", response_model=ExecutionStatusRead)
def get_status(execution_id: str, db: Session = Depends(get_db)) -> ExecutionStatusRead:
    execution = _get_execution_or_404(db, execution_id)
    return ExecutionStatusRead.model_validate(execution)


@router.get("/{execution_id}/logs", response_model=ExecutionLogsRead)
def get_logs(execution_id: str, db: Session = Depends(get_db)) -> ExecutionLogsRead:
    _get_execution_or_404(db, execution_id)
    rows = events.list_events(db, execution_id)
    entries = [
        ExecutionLogEntry(
            sequence=row.sequence,
            timestamp=row.occurred_at,
            kind=row.kind,
            level=row.level,
            message=row.message,
        )
        for row in rows
    ]
    return ExecutionLogsRead(execution_id=execution_id, entries=entries)


@router.get("/{execution_id}/artefacts", response_model=ExecutionArtefactsRead)
def get_artefacts(execution_id: str, db: Session = Depends(get_db)) -> ExecutionArtefactsRead:
    _get_execution_or_404(db, execution_id)
    artefacts = events.list_artefacts(db, execution_id)
    return ExecutionArtefactsRead(
        execution_id=execution_id,
        artefacts=[ExecutionArtefact.model_validate(a) for a in artefacts],
    )


@router.post("/{execution_id}/cancel", response_model=ExecutionCancelRead)
def cancel_execution(execution_id: str, db: Session = Depends(get_db)) -> ExecutionCancelRead:
    execution = _get_execution_or_404(db, execution_id)
    if execution.status in (ExecutionStatus.CANCELLED.value, ExecutionStatus.DONE.value):
        return ExecutionCancelRead(
            execution_id=execution_id, status=execution.status, requested=False
        )
    execution = executions.transition(db, execution, ExecutionStatus.CANCELLED)
    return ExecutionCancelRead(execution_id=execution_id, status=execution.status, requested=True)


@router.post("/{execution_id}/cleanup", response_model=ExecutionCleanupRead)
def cleanup_execution(
    execution_id: str,
    db: Session = Depends(get_db),
    docker: DockerClient = Depends(get_docker_client),
) -> ExecutionCleanupRead:
    execution = _get_execution_or_404(db, execution_id)
    if execution.status not in (
        ExecutionStatus.CANCELLED.value,
        ExecutionStatus.SUCCEEDED.value,
        ExecutionStatus.FAILED.value,
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Execution is not in a cleanable terminal state",
        )
    execution = executor.cleanup(db, execution, docker)
    return ExecutionCleanupRead(execution_id=execution_id, status=execution.status, cleaned=True)


@router.post("/recover", response_model=ExecutionList)
def recover_orphans_endpoint(
    db: Session = Depends(get_db),
    docker: DockerClient = Depends(get_docker_client),
) -> ExecutionList:
    """Recover orphaned executions left by a worker/infra failure (3.8)."""
    recovered = executor.recover(db, docker, get_settings())
    return ExecutionList(
        items=[ExecutionRead.model_validate(e) for e in recovered],
        total=len(recovered),
    )
