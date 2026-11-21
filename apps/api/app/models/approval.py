"""Plan-approval gate ORM model (Phase 5.4).

A workflow requiring operator approval carries a ``PlanApproval`` record that
captures the approval request, the operator's decision, their comments, and
the timestamp. Development is gated on a recorded ``approved`` decision
(FR-8, README §10.2). The record is the durable, attributable evidence of the
gate, not the agent conversation.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base

if TYPE_CHECKING:
    from app.models.workflow_instance import Workflow


class ApprovalStatus(StrEnum):
    """Lifecycle of a plan-approval request."""

    REQUESTED = "requested"
    APPROVED = "approved"
    REJECTED = "rejected"


class PlanApproval(Base):
    __tablename__ = "plan_approvals"

    id: Mapped[int] = mapped_column(primary_key=True)
    workflow_id: Mapped[int] = mapped_column(
        ForeignKey("workflows.id"), nullable=False, index=True, unique=True
    )
    status: Mapped[str] = mapped_column(
        String(24), nullable=False, server_default=ApprovalStatus.REQUESTED.value, index=True
    )
    # The plan summary + evidence presented to the operator at request time.
    plan_summary: Mapped[str | None] = mapped_column(Text)
    evidence_refs: Mapped[str | None] = mapped_column(Text)

    # Decision record: who decided, what they said, when.
    approver_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    approver_email: Mapped[str | None] = mapped_column(String(255))
    decision_comment: Mapped[str | None] = mapped_column(Text)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    workflow: Mapped[Workflow] = relationship(back_populates="approval")
