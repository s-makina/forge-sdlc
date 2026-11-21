"""Plan-approval gate service (Phase 5.4).

Owns the plan-approval record lifecycle: requesting approval against a
workflow, deciding (approve/reject) as the operator, and gating whether
development may proceed. A workflow with a plan-approval record is parked in
``WAITING_APPROVAL`` until an ``approved`` decision is recorded; a rejection
returns it to ``pending`` so planning can be revisited (FR-8, README §10.2).
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.approval import ApprovalStatus, PlanApproval
from app.models.workflow_instance import Workflow, WorkflowStatus


class ApprovalNotFound(LookupError):
    pass


class WorkflowAlreadyApproved(RuntimeError):
    pass


def request_approval(
    db: Session,
    workflow: Workflow,
    *,
    plan_summary: str | None = None,
    evidence_refs: str | None = None,
) -> PlanApproval:
    """Create (or return) a pending plan-approval request and gate the workflow.

    The workflow is moved to ``WAITING_APPROVAL`` so development is blocked
    until the operator records a decision. If a request already exists for the
    workflow it is returned unchanged.
    """
    existing = get_approval(db, workflow.id)
    if existing is not None:
        return existing
    approval = PlanApproval(
        workflow_id=workflow.id,
        status=ApprovalStatus.REQUESTED.value,
        plan_summary=plan_summary,
        evidence_refs=evidence_refs,
    )
    db.add(approval)
    workflow.status = WorkflowStatus.WAITING_APPROVAL.value
    db.commit()
    db.refresh(approval)
    return approval


def decide(
    db: Session,
    workflow: Workflow,
    decision: str,
    *,
    approver_id: int,
    approver_email: str,
    comment: str | None = None,
) -> PlanApproval:
    """Record the operator's decision on a workflow's plan approval.

    Approving releases the workflow back to ``pending`` for planning/development
    to resume; rejecting also returns it to ``pending`` (planning re-runs). Raises
    ``ApprovalNotFound`` when no request exists and ``WorkflowAlreadyApproved``
    when the request was already decided.
    """
    approval = get_approval(db, workflow.id)
    if approval is None:
        raise ApprovalNotFound(f"no plan approval for workflow {workflow.id}")
    if approval.status != ApprovalStatus.REQUESTED.value:
        raise WorkflowAlreadyApproved(f"plan approval for workflow {workflow.id} already decided")
    approval.status = ApprovalStatus(decision).value
    approval.approver_id = approver_id
    approval.approver_email = approver_email
    approval.decision_comment = comment
    approval.decided_at = datetime.now(UTC)
    workflow.status = WorkflowStatus.PENDING.value
    db.commit()
    db.refresh(approval)
    return approval


def is_approved(db: Session, workflow: Workflow) -> bool:
    """Return True when the workflow's plan approval has been approved."""
    approval = get_approval(db, workflow.id)
    return approval is not None and approval.status == ApprovalStatus.APPROVED.value


def get_approval(db: Session, workflow_id: int) -> PlanApproval | None:
    return db.scalar(select(PlanApproval).where(PlanApproval.workflow_id == workflow_id))


def list_approvals(db: Session) -> list[PlanApproval]:
    return list(db.scalars(select(PlanApproval).order_by(PlanApproval.id.desc())).all())
