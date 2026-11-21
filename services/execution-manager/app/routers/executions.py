"""Execution API routes.

Exposes the Phase 3.1 API surface plus the Phase 3.2 workspace-lifecycle
endpoints: request execution, poll status, fetch logs/artefacts, cancel, and
cleanup, plus provisioning a workspace container.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.deps.container import get_docker_client
from app.docker.client import DockerClient
from app.models.execution import Execution, ExecutionStatus
from app.schemas.execution import (
    ExecutionArtefactsRead,
    ExecutionCancelRead,
    ExecutionCleanupRead,
    ExecutionCreate,
    ExecutionList,
    ExecutionLogsRead,
    ExecutionRead,
    ExecutionStatusRead,
)
from app.services import executions, executor

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
    # Log capture is implemented in Phase 3.7.
    return ExecutionLogsRead(execution_id=execution_id, entries=[])


@router.get("/{execution_id}/artefacts", response_model=ExecutionArtefactsRead)
def get_artefacts(execution_id: str, db: Session = Depends(get_db)) -> ExecutionArtefactsRead:
    _get_execution_or_404(db, execution_id)
    # Artefact storage is implemented in Phase 3.7.
    return ExecutionArtefactsRead(execution_id=execution_id, artefacts=[])


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