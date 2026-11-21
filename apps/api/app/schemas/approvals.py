"""Plan-approval gate schemas (Phase 5.4)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ApprovalStatusValue = Literal["requested", "approved", "rejected"]
ApprovalDecisionValue = Literal["approved", "rejected"]


class ApprovalRequest(BaseModel):
    """An operator's decision on a pending plan-approval request."""

    decision: ApprovalDecisionValue
    comment: str | None = Field(default=None, max_length=2000)


class PlanApprovalRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    workflow_id: int
    status: str
    plan_summary: str | None
    evidence_refs: str | None
    approver_id: int | None
    approver_email: str | None
    decision_comment: str | None
    decided_at: datetime | None
    requested_at: datetime


class PlanApprovalList(BaseModel):
    items: list[PlanApprovalRead]
    total: int
