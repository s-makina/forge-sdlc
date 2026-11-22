"""Store encrypted model provider credentials.

Revision ID: 0005_provider_credentials
Revises: 0004_plan_approvals
Create Date: 2026-11-22
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0005_provider_credentials"
down_revision: str | None = "0004_plan_approvals"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "model_providers",
        sa.Column("credential_ciphertext", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("model_providers", "credential_ciphertext")
