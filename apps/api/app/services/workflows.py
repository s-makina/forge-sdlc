"""Workflow template and instance service operations (Phase 4.2/4.7).

Owns reusable workflow templates (stages + agent roles + dependencies) and
concrete workflow instances created from them with typed inputs (README §10).
A template can be seeded from the built-in definitions (feature-development,
bug-fix, refactoring) or created via the API.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.workflow import WorkflowStage, WorkflowTemplate
from app.models.workflow_instance import Workflow, WorkflowStageRun, WorkflowStatus
from app.schemas.workflows import StageDefinition, WorkflowCreate, WorkflowTemplateCreate


class TemplateNotFound(LookupError):
    pass


class WorkflowNotFound(LookupError):
    pass


class DuplicateTemplateSlug(ValueError):
    pass


def _template_with_stages(db: Session, template_id: int) -> WorkflowTemplate | None:
    stmt = (
        select(WorkflowTemplate)
        .where(WorkflowTemplate.id == template_id)
        .options(selectinload(WorkflowTemplate.stages))
    )
    return db.scalar(stmt)


def _workflow_with_stages(db: Session, workflow_id: int) -> Workflow | None:
    stmt = (
        select(Workflow)
        .where(Workflow.id == workflow_id)
        .options(selectinload(Workflow.stages))
    )
    return db.scalar(stmt)


def list_templates(db: Session, *, include_inactive: bool = False) -> list[WorkflowTemplate]:
    stmt = select(WorkflowTemplate).options(selectinload(WorkflowTemplate.stages))
    if not include_inactive:
        stmt = stmt.where(WorkflowTemplate.is_active.is_(True))
    return list(db.scalars(stmt.order_by(WorkflowTemplate.slug)).all())


def get_template(db: Session, template_id: int) -> WorkflowTemplate | None:
    return _template_with_stages(db, template_id)


def create_template(db: Session, payload: WorkflowTemplateCreate) -> WorkflowTemplate:
    if db.scalar(select(WorkflowTemplate).where(WorkflowTemplate.slug == payload.slug)) is not None:
        raise DuplicateTemplateSlug(f"template '{payload.slug}' already exists")
    template = WorkflowTemplate(
        slug=payload.slug,
        name=payload.name,
        description=payload.description,
        category=payload.category,
        input_schema=dict(payload.input_schema),
    )
    db.add(template)
    db.flush()
    for position, stage in enumerate(payload.stages):
        template.stages.append(_build_stage(stage, position))
    db.commit()
    refreshed = _template_with_stages(db, template.id)
    assert refreshed is not None
    return refreshed


def _build_stage(stage: StageDefinition, position: int) -> WorkflowStage:
    return WorkflowStage(
        position=position,
        name=stage.name,
        agent_role=stage.agent_role,
        depends_on=list(stage.depends_on),
    )


def create_workflow(db: Session, payload: WorkflowCreate) -> Workflow:
    """Instantiate a workflow from a template, creating its stage runs."""
    template = _template_with_stages(db, payload.template_id)
    if template is None:
        raise TemplateNotFound(f"template {payload.template_id} not found")
    workflow = Workflow(
        project_id=payload.project_id,
        template_id=template.id,
        name=payload.name,
        status=WorkflowStatus.PENDING.value,
        inputs=dict(payload.inputs),
    )
    db.add(workflow)
    db.flush()
    for stage in template.stages:
        workflow.stages.append(
            WorkflowStageRun(
                position=stage.position,
                name=stage.name,
                agent_role=stage.agent_role,
                status="pending",
            )
        )
    db.commit()
    refreshed = _workflow_with_stages(db, workflow.id)
    assert refreshed is not None
    return refreshed


def list_workflows(db: Session, *, project_id: int | None = None) -> list[Workflow]:
    stmt = select(Workflow).options(selectinload(Workflow.stages))
    if project_id is not None:
        stmt = stmt.where(Workflow.project_id == project_id)
    return list(db.scalars(stmt.order_by(Workflow.id)).all())


def get_workflow(db: Session, workflow_id: int) -> Workflow | None:
    return _workflow_with_stages(db, workflow_id)


def transition_workflow(db: Session, workflow: Workflow, status: str, *, note: str | None = None) -> Workflow:
    """Move a workflow instance to ``status``, recording timing."""
    now = datetime.now(timezone.utc)
    if status == WorkflowStatus.RUNNING.value and workflow.started_at is None:
        workflow.started_at = now
    if status in (
        WorkflowStatus.SUCCEEDED.value,
        WorkflowStatus.FAILED.value,
        WorkflowStatus.CANCELLED.value,
    ):
        workflow.finished_at = now
    if note:
        workflow.error_message = note
    workflow.status = status
    db.commit()
    refreshed = _workflow_with_stages(db, workflow.id)
    assert refreshed is not None
    return refreshed


def transition_stage(
    db: Session,
    workflow: Workflow,
    position: int,
    status: str,
    *,
    error_message: str | None = None,
) -> WorkflowStageRun:
    """Transition a single stage run within a workflow instance."""
    stage = next((s for s in workflow.stages if s.position == position), None)
    if stage is None:
        raise WorkflowNotFound(f"stage at position {position} not found")
    now = datetime.now(timezone.utc)
    if status == "running" and stage.started_at is None:
        stage.started_at = now
    if status in ("succeeded", "failed", "cancelled"):
        stage.finished_at = now
    if error_message is not None:
        stage.error_message = error_message
    stage.status = status
    db.commit()
    db.refresh(stage)
    return stage


def seed_default_templates(db: Session) -> int:
    """Seed the built-in MVP templates if not already present. Returns count created."""
    created = 0
    definitions = _default_template_definitions()
    for definition in definitions:
        existing = db.scalar(
            select(WorkflowTemplate).where(WorkflowTemplate.slug == definition.slug)
        )
        if existing is not None:
            continue
        create_template(db, definition)
        created += 1
    return created


def _default_template_definitions() -> list[WorkflowTemplateCreate]:
    return [
        WorkflowTemplateCreate(
            slug="feature-development",
            name="Feature Development",
            category="feature",
            description="Primary feature-development workflow from requirements to a completed PR.",
            stages=[
                StageDefinition(name="requirements", agent_role="business_analyst"),
                StageDefinition(name="architecture", agent_role="software_architect", depends_on=["requirements"]),
                StageDefinition(name="planning", agent_role="project_manager", depends_on=["architecture"]),
                StageDefinition(name="implementation", agent_role="software_engineer", depends_on=["planning"]),
                StageDefinition(name="testing", agent_role="qa_engineer", depends_on=["implementation"]),
                StageDefinition(name="review", agent_role="code_reviewer", depends_on=["testing"]),
                StageDefinition(name="release", agent_role="project_manager", depends_on=["review"]),
            ],
        ),
        WorkflowTemplateCreate(
            slug="bug-fix",
            name="Bug Fix",
            category="bugfix",
            description="A focused workflow for fixing a reported defect.",
            stages=[
                StageDefinition(name="triage", agent_role="software_engineer"),
                StageDefinition(name="fix", agent_role="software_engineer", depends_on=["triage"]),
                StageDefinition(name="verify", agent_role="qa_engineer", depends_on=["fix"]),
            ],
        ),
        WorkflowTemplateCreate(
            slug="refactoring",
            name="Refactoring",
            category="refactoring",
            description="Improve internal structure without changing behaviour.",
            stages=[
                StageDefinition(name="analysis", agent_role="software_architect"),
                StageDefinition(name="refactor", agent_role="software_engineer", depends_on=["analysis"]),
                StageDefinition(name="verify", agent_role="qa_engineer", depends_on=["refactor"]),
            ],
        ),
    ]