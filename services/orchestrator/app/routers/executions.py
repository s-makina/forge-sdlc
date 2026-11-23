"""Execution-run routes for the orchestrator worker (Phase 4.4/4.6).

Expose the durable execution-run surface: start a coding pipeline for an
already-created execution, query its durable status, and cancel it. The
execution record is created by the control-plane API; this service drives the
remaining pipeline steps durably through Temporal.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.core.container import Container, get_container
from app.services.orchestrator import ExecutionRunSubmission

router = APIRouter(tags=["executions"])


class ExecutionRunStartRequest(BaseModel):
    execution_id: str = Field(min_length=1, max_length=64)
    task_id: str = Field(default="", max_length=64)
    project_id: int = Field(default=0, ge=0)
    prompt: str = Field(default="", max_length=8000)


class ExecutionRunStatusResponse(BaseModel):
    execution_id: str
    durable_status: str


@router.post("/executions/{execution_id}/start-run", response_model=ExecutionRunStatusResponse)
def start_execution_run(
    execution_id: str, payload: ExecutionRunStartRequest
) -> ExecutionRunStatusResponse:
    if payload.execution_id != execution_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="execution_id in path and body must match",
        )
    submission = ExecutionRunSubmission(
        execution_id=payload.execution_id,
        task_id=payload.task_id,
        project_id=payload.project_id,
        prompt=payload.prompt,
    )
    container: Container = get_container()
    run = container.orchestrator.start_execution_run(submission)
    return ExecutionRunStatusResponse(
        execution_id=execution_id, durable_status=run.status
    )


@router.post("/executions/{execution_id}/cancel-run", response_model=ExecutionRunStatusResponse)
def cancel_execution_run(execution_id: str) -> ExecutionRunStatusResponse:
    container: Container = get_container()
    container.orchestrator.cancel_execution_run(execution_id)
    return ExecutionRunStatusResponse(execution_id=execution_id, durable_status="cancelled")


@router.get("/executions/{execution_id}/run-status", response_model=ExecutionRunStatusResponse)
def execution_run_status(execution_id: str) -> ExecutionRunStatusResponse:
    container: Container = get_container()
    durable = container.orchestrator.execution_run_status(execution_id)
    return ExecutionRunStatusResponse(execution_id=execution_id, durable_status=durable)
