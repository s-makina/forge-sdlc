"""phase 2: agent and model management

Revision ID: 0002_agents_models
Revises: 0001_initial
Create Date: 2026-11-19
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0002_agents_models"
down_revision: str | None = "0001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "tools",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("input_schema", sa.JSON(), nullable=False),
        sa.Column("required_permissions", sa.JSON(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_tools_name", "tools", ["name"], unique=True)

    op.create_table(
        "skills",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("instructions", sa.Text(), nullable=True),
        sa.Column("files", sa.JSON(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_skills_name", "skills", ["name"], unique=True)

    op.create_table(
        "model_providers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("provider_type", sa.String(length=32), nullable=False),
        sa.Column("base_url", sa.String(length=1024), nullable=False),
        sa.Column("credential_ref", sa.String(length=255), nullable=True),
        sa.Column("timeout_seconds", sa.Integer(), server_default="60", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="1", nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_model_providers_name", "model_providers", ["name"], unique=True)

    op.create_table(
        "models",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("provider_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=True),
        sa.Column("capabilities", sa.JSON(), nullable=False),
        sa.Column("context_window", sa.Integer(), nullable=True),
        sa.Column("input_cost_per_million", sa.Float(), nullable=True),
        sa.Column("output_cost_per_million", sa.Float(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="1", nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["provider_id"], ["model_providers.id"]),
        sa.UniqueConstraint("provider_id", "name", name="uq_models_provider_name"),
    )
    op.create_index("ix_models_provider_id", "models", ["provider_id"])

    op.create_table(
        "model_profiles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("primary_model_id", sa.Integer(), nullable=True),
        sa.Column("fallback_model_ids", sa.JSON(), nullable=False),
        sa.Column("required_capabilities", sa.JSON(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="1", nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["primary_model_id"], ["models.id"]),
    )
    op.create_index("ix_model_profiles_name", "model_profiles", ["name"], unique=True)
    op.create_index("ix_model_profiles_primary_model_id", "model_profiles", ["primary_model_id"])

    op.create_table(
        "agents",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("slug", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=128), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="1", nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_agents_slug", "agents", ["slug"], unique=True)
    op.create_index("ix_agents_role", "agents", ["role"])

    op.create_table(
        "agent_versions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("agent_id", sa.Integer(), nullable=False),
        sa.Column("version", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=16), server_default="draft", nullable=False),
        sa.Column("instructions", sa.Text(), nullable=False),
        sa.Column("capabilities", sa.JSON(), nullable=False),
        sa.Column("model_profile", sa.String(length=64), nullable=False),
        sa.Column("quality_gates", sa.JSON(), nullable=False),
        sa.Column("definition_hash", sa.String(length=64), nullable=True),
        sa.Column("source", sa.String(length=32), server_default="yaml", nullable=False),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("retired_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["agent_id"], ["agents.id"]),
        sa.UniqueConstraint("agent_id", "version", name="uq_agent_versions_agent_version"),
    )
    op.create_index("ix_agent_versions_agent_id", "agent_versions", ["agent_id"])
    op.create_index("ix_agent_versions_status", "agent_versions", ["status"])
    # At most one active version per agent (README 8.5).
    op.create_index(
        "uq_agent_versions_one_active",
        "agent_versions",
        ["agent_id"],
        unique=True,
        postgresql_where=sa.text("status = 'active'"),
        sqlite_where=sa.text("status = 'active'"),
    )

    op.create_table(
        "agent_skills",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("agent_version_id", sa.Integer(), nullable=False),
        sa.Column("skill_name", sa.String(length=255), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["agent_version_id"], ["agent_versions.id"]),
        sa.UniqueConstraint("agent_version_id", "skill_name", name="uq_agent_skills_version_name"),
    )
    op.create_index("ix_agent_skills_agent_version_id", "agent_skills", ["agent_version_id"])

    op.create_table(
        "agent_tool_permissions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("agent_version_id", sa.Integer(), nullable=False),
        sa.Column("tool_name", sa.String(length=255), nullable=False),
        sa.Column("permissions", sa.JSON(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["agent_version_id"], ["agent_versions.id"]),
        sa.UniqueConstraint(
            "agent_version_id", "tool_name", name="uq_agent_tool_version_tool"
        ),
    )
    op.create_index(
        "ix_agent_tool_permissions_agent_version_id",
        "agent_tool_permissions",
        ["agent_version_id"],
    )

    op.create_table(
        "provider_checks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("provider_id", sa.Integer(), nullable=False),
        sa.Column("model_id", sa.Integer(), nullable=True),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("capability", sa.String(length=32), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("latency_ms", sa.Float(), nullable=True),
        sa.Column("detail", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["provider_id"], ["model_providers.id"]),
        sa.ForeignKeyConstraint(["model_id"], ["models.id"]),
    )
    op.create_index("ix_provider_checks_provider_id", "provider_checks", ["provider_id"])

    op.create_table(
        "usage_records",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("provider_id", sa.Integer(), nullable=True),
        sa.Column("model_id", sa.Integer(), nullable=True),
        sa.Column("profile_name", sa.String(length=64), nullable=True),
        sa.Column("agent_version_id", sa.Integer(), nullable=True),
        sa.Column("input_tokens", sa.Integer(), server_default="0", nullable=False),
        sa.Column("output_tokens", sa.Integer(), server_default="0", nullable=False),
        sa.Column("total_tokens", sa.Integer(), server_default="0", nullable=False),
        sa.Column("cost_usd", sa.Float(), nullable=True),
        sa.Column("success", sa.Boolean(), server_default="1", nullable=False),
        sa.Column("latency_ms", sa.Float(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["provider_id"], ["model_providers.id"]),
        sa.ForeignKeyConstraint(["model_id"], ["models.id"]),
        sa.ForeignKeyConstraint(["agent_version_id"], ["agent_versions.id"]),
    )
    op.create_index("ix_usage_records_provider_id", "usage_records", ["provider_id"])
    op.create_index("ix_usage_records_model_id", "usage_records", ["model_id"])
    op.create_index("ix_usage_records_profile_name", "usage_records", ["profile_name"])
    op.create_index("ix_usage_records_agent_version_id", "usage_records", ["agent_version_id"])


def downgrade() -> None:
    op.drop_table("usage_records")
    op.drop_table("provider_checks")
    op.drop_table("agent_tool_permissions")
    op.drop_table("agent_skills")
    op.drop_table("agent_versions")
    op.drop_table("agents")
    op.drop_table("model_profiles")
    op.drop_table("models")
    op.drop_table("model_providers")
    op.drop_table("skills")
    op.drop_table("tools")
