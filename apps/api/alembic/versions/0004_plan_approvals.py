"""phase 5: plan-approval gate

Revision ID: 0004_plan_approvals
Revises: 0003_workflows_tasks
Create Date: 2026-11-21
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0004_plan_approvals"
down_revision: str | None = "0003_workflows_tasks"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "plan_approvals",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("workflow_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=24), server_default="requested", nullable=False),
        sa.Column("plan_summary", sa.Text(), nullable=True),
        sa.Column("evidence_refs", sa.Text(), nullable=True),
        sa.Column("approver_id", sa.Integer(), nullable=True),
        sa.Column("approver_email", sa.String(length=255), nullable=True),
        sa.Column("decision_comment", sa.Text(), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "requested_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["workflow_id"], ["workflows.id"]),
        sa.ForeignKeyConstraint(["approver_id"], ["users.id"]),
        sa.UniqueConstraint("workflow_id", name="uq_plan_approvals_workflow_id"),
    )
    op.create_index("ix_plan_approvals_workflow_id", "plan_approvals", ["workflow_id"])
    op.create_index("ix_plan_approvals_status", "plan_approvals", ["status"])


def downgrade() -> None:
    op.drop_table("plan_approvals")
