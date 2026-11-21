"""Workflow routes for the orchestrator worker (Phase 4.1).

These expose the durable-workflow submission surface: submit a workflow run,
request cancellation, and read back durable status. The orchestrator mirrors
the control-plane workflow lifecycle.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.core.container import Container, get_container
from app.services.orchestrator import WorkflowSubmission

router = APIRouter(tags=["workflows"])


class WorkflowStartRequest(BaseModel):
    workflow_id: int = Field(gt=0)
    project_id: int = Field(gt=0)
    template_slug: str = Field(min_length=1, max_length=64)
    inputs: dict[str, object] = {}


class WorkflowStatusResponse(BaseModel):
    workflow_id: int
    durable_status: str


@router.post("/workflows/{workflow_id}/start", response_model=WorkflowStatusResponse)
def start_workflow(workflow_id: int, payload: WorkflowStartRequest) -> WorkflowStatusResponse:
    if payload.workflow_id != workflow_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="workflow_id in path and body must match",
        )
    submission = WorkflowSubmission(
        workflow_id=payload.workflow_id,
        project_id=payload.project_id,
        template_slug=payload.template_slug,
        inputs=dict(payload.inputs),
    )
    container: Container = get_container()
    run = container.orchestrator.start(submission)
    return WorkflowStatusResponse(workflow_id=workflow_id, durable_status=run.status)


@router.post("/workflows/{workflow_id}/cancel", response_model=WorkflowStatusResponse)
def cancel_workflow(workflow_id: int) -> WorkflowStatusResponse:
    container: Container = get_container()
    container.orchestrator.cancel(workflow_id)
    return WorkflowStatusResponse(workflow_id=workflow_id, durable_status="cancelled")


@router.get("/workflows/{workflow_id}/status", response_model=WorkflowStatusResponse)
def workflow_status(workflow_id: int) -> WorkflowStatusResponse:
    container: Container = get_container()
    durable = container.orchestrator.status(workflow_id)
    return WorkflowStatusResponse(workflow_id=workflow_id, durable_status=durable)