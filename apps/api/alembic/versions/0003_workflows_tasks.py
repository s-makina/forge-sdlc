"""phase 4: workflow orchestration - templates, instances, tasks

Revision ID: 0003_workflows_tasks
Revises: 0002_agents_models
Create Date: 2026-11-21
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0003_workflows_tasks"
down_revision: str | None = "0002_agents_models"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "workflow_templates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("slug", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("category", sa.String(length=32), server_default="feature", nullable=False),
        sa.Column("input_schema", sa.JSON(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="1", nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_workflow_templates_slug", "workflow_templates", ["slug"], unique=True)

    op.create_table(
        "workflow_stages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("template_id", sa.Integer(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("agent_role", sa.String(length=128), nullable=False),
        sa.Column("depends_on", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["template_id"], ["workflow_templates.id"]),
        sa.UniqueConstraint("template_id", "position", name="uq_workflow_stages_position"),
    )
    op.create_index("ix_workflow_stages_template_id", "workflow_stages", ["template_id"])

    op.create_table(
        "workflows",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("template_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="pending", nullable=False),
        sa.Column("inputs", sa.JSON(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["template_id"], ["workflow_templates.id"]),
    )
    op.create_index("ix_workflows_project_id", "workflows", ["project_id"])
    op.create_index("ix_workflows_template_id", "workflows", ["template_id"])
    op.create_index("ix_workflows_status", "workflows", ["status"])

    op.create_table(
        "workflow_stage_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("workflow_id", sa.Integer(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("agent_role", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=24), server_default="pending", nullable=False),
        sa.Column("retries", sa.Integer(), server_default="0", nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["workflow_id"], ["workflows.id"]),
    )
    op.create_index("ix_workflow_stage_runs_workflow_id", "workflow_stage_runs", ["workflow_id"])

    op.create_table(
        "tasks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("workflow_id", sa.Integer(), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("task_type", sa.String(length=32), server_default="feature", nullable=False),
        sa.Column("priority", sa.String(length=16), server_default="medium", nullable=False),
        sa.Column("status", sa.String(length=24), server_default="draft", nullable=False),
        sa.Column("acceptance_criteria", sa.Text(), nullable=True),
        sa.Column("repository_url", sa.String(length=1024), nullable=True),
        sa.Column("target_branch", sa.String(length=255), server_default="main", nullable=False),
        sa.Column("assigned_role", sa.String(length=128), nullable=True),
        sa.Column("assigned_agent_id", sa.Integer(), nullable=True),
        sa.Column("skills", sa.JSON(), nullable=False),
        sa.Column("model_profile", sa.String(length=64), nullable=True),
        sa.Column("relevant_files", sa.JSON(), nullable=False),
        sa.Column("cpu_limit", sa.Float(), nullable=True),
        sa.Column("memory_limit", sa.String(length=32), nullable=True),
        sa.Column("disk_limit", sa.String(length=32), nullable=True),
        sa.Column("timeout_seconds", sa.Integer(), nullable=True),
        sa.Column("network_policy", sa.String(length=32), nullable=True),
        sa.Column("result_summary", sa.Text(), nullable=True),
        sa.Column("artefact_refs", sa.JSON(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["assigned_agent_id"], ["agents.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["workflow_id"], ["workflows.id"]),
    )
    op.create_index("ix_tasks_project_id", "tasks", ["project_id"])
    op.create_index("ix_tasks_workflow_id", "tasks", ["workflow_id"])
    op.create_index("ix_tasks_status", "tasks", ["status"])
    op.create_index("ix_tasks_task_type", "tasks", ["task_type"])
    op.create_index("ix_tasks_assigned_agent_id", "tasks", ["assigned_agent_id"])

    op.create_table(
        "task_dependencies",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("task_id", sa.Integer(), nullable=False),
        sa.Column("depends_on_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"]),
        sa.ForeignKeyConstraint(["depends_on_id"], ["tasks.id"]),
        sa.UniqueConstraint("task_id", "depends_on_id", name="uq_task_dependencies_edge"),
    )
    op.create_index("ix_task_dependencies_task_id", "task_dependencies", ["task_id"])
    op.create_index("ix_task_dependencies_depends_on_id", "task_dependencies", ["depends_on_id"])


def downgrade() -> None:
    op.drop_table("task_dependencies")
    op.drop_table("tasks")
    op.drop_table("workflow_stage_runs")
    op.drop_table("workflows")
    op.drop_table("workflow_stages")
    op.drop_table("workflow_templates")