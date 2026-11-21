"""Plan-approval gate routes (Phase 5.4).

Expose the operator's approval surface: list pending/decided plan approvals,
read one by workflow, request approval for a workflow, and record an approve or
reject decision. Approving or rejecting a request gates the workflow's
development (FR-8, README §10.2).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.deps.auth import require_user
from app.models.user import User
from app.schemas.approvals import ApprovalRequest, PlanApprovalList, PlanApprovalRead
from app.services import approvals, audit, workflows

router = APIRouter(prefix="/approvals", tags=["approvals"])


def _get_workflow_or_404(db: Session, workflow_id: int):
    workflow = workflows.get_workflow(db, workflow_id)
    if workflow is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found"
        )
    return workflow


def _get_approval_or_404(db: Session, workflow_id: int):
    approval = approvals.get_approval(db, workflow_id)
    if approval is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Plan approval not found"
        )
    return approval


@router.get("", response_model=PlanApprovalList)
def list_approvals(
    db: Session = Depends(get_db),
    _: User = Depends(require_user),
) -> PlanApprovalList:
    items = approvals.list_approvals(db)
    return PlanApprovalList(
        items=[PlanApprovalRead.model_validate(a) for a in items], total=len(items)
    )


@router.get("/workflows/{workflow_id}", response_model=PlanApprovalRead)
def get_approval(
    workflow_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_user),
) -> PlanApprovalRead:
    return PlanApprovalRead.model_validate(_get_approval_or_404(db, workflow_id))


@router.post(
    "/workflows/{workflow_id}/request",
    response_model=PlanApprovalRead,
    status_code=status.HTTP_201_CREATED,
)
def request_approval(
    workflow_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
) -> PlanApprovalRead:
    workflow = _get_workflow_or_404(db, workflow_id)
    approval = approvals.request_approval(db, workflow)
    audit.record_audit(
        db,
        action="approval.request",
        entity_type="plan_approval",
        entity_id=str(approval.id),
        actor_id=user.id,
        actor_email=user.email,
        details=f"Requested plan approval for workflow {workflow.id}",
    )
    return PlanApprovalRead.model_validate(approval)


@router.post("/workflows/{workflow_id}/decide", response_model=PlanApprovalRead)
def decide_approval(
    workflow_id: int,
    payload: ApprovalRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
) -> PlanApprovalRead:
    workflow = _get_workflow_or_404(db, workflow_id)
    try:
        approval = approvals.decide(
            db,
            workflow,
            payload.decision,
            approver_id=user.id,
            approver_email=user.email,
            comment=payload.comment,
        )
    except approvals.ApprovalNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from None
    except approvals.WorkflowAlreadyApproved as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from None
    audit.record_audit(
        db,
        action="approval.decide",
        entity_type="plan_approval",
        entity_id=str(approval.id),
        actor_id=user.id,
        actor_email=user.email,
        details=f"Workflow {workflow.id} plan approval -> {payload.decision}",
    )
    return PlanApprovalRead.model_validate(approval)
