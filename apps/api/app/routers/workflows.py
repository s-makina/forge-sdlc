"""Workflow template and instance routes (Phase 4.2/4.7)."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.deps.auth import require_user
from app.models.user import User
from app.models.workflow import WorkflowTemplate
from app.models.workflow_instance import Workflow
from app.schemas.workflows import (
    StageTransition,
    WorkflowCreate,
    WorkflowList,
    WorkflowRead,
    WorkflowTemplateCreate,
    WorkflowTemplateList,
    WorkflowTemplateRead,
    WorkflowTransition,
)
from app.services import audit, engine, scheduling, workflows

router = APIRouter(prefix="/workflows", tags=["workflows"])


def _get_template_or_404(db: Session, template_id: int) -> WorkflowTemplate:
    template = workflows.get_template(db, template_id)
    if template is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow template not found")
    return template


def _get_workflow_or_404(db: Session, workflow_id: int) -> Workflow:
    workflow = workflows.get_workflow(db, workflow_id)
    if workflow is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found")
    return workflow


# --- Workflow templates -----------------------------------------------------


@router.get("/templates", response_model=WorkflowTemplateList)
def list_templates(
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    _: User = Depends(require_user),
) -> WorkflowTemplateList:
    items = workflows.list_templates(db, include_inactive=include_inactive)
    return WorkflowTemplateList(
        items=[WorkflowTemplateRead.model_validate(t) for t in items], total=len(items)
    )


@router.post("/templates", response_model=WorkflowTemplateRead, status_code=status.HTTP_201_CREATED)
def create_template(
    payload: WorkflowTemplateCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
) -> WorkflowTemplateRead:
    try:
        template = workflows.create_template(db, payload)
    except workflows.DuplicateTemplateSlug as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from None
    audit.record_audit(
        db,
        action="workflow_template.create",
        entity_type="workflow_template",
        entity_id=str(template.id),
        actor_id=user.id,
        actor_email=user.email,
        details=f"Created workflow template '{template.slug}'",
    )
    return WorkflowTemplateRead.model_validate(template)


@router.get("/templates/{template_id}", response_model=WorkflowTemplateRead)
def get_template(
    template_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_user),
) -> WorkflowTemplateRead:
    return WorkflowTemplateRead.model_validate(_get_template_or_404(db, template_id))


# --- Workflow instances ------------------------------------------------------


@router.get("", response_model=WorkflowList)
def list_workflows(
    project_id: int | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_user),
) -> WorkflowList:
    items = workflows.list_workflows(db, project_id=project_id)
    return WorkflowList(items=[WorkflowRead.model_validate(w) for w in items], total=len(items))


@router.post("", response_model=WorkflowRead, status_code=status.HTTP_201_CREATED)
def create_workflow(
    payload: WorkflowCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
) -> WorkflowRead:
    try:
        workflow = workflows.create_workflow(db, payload)
    except workflows.TemplateNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from None
    audit.record_audit(
        db,
        action="workflow.create",
        entity_type="workflow",
        entity_id=str(workflow.id),
        actor_id=user.id,
        actor_email=user.email,
        details=f"Created workflow '{workflow.name}'",
    )
    return WorkflowRead.model_validate(workflow)


@router.post("/{workflow_id}/schedule", response_model=WorkflowRead)
def schedule_workflow(
    workflow_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
) -> WorkflowRead:
    workflow = _get_workflow_or_404(db, workflow_id)
    workflow = scheduling.start_workflow(db, workflow)
    audit.record_audit(
        db,
        action="workflow.schedule",
        entity_type="workflow",
        entity_id=str(workflow.id),
        actor_id=user.id,
        actor_email=user.email,
        details=f"Scheduled workflow '{workflow.name}'",
    )
    return WorkflowRead.model_validate(workflow)


@router.get("/{workflow_id}", response_model=WorkflowRead)
def get_workflow(
    workflow_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_user),
) -> WorkflowRead:
    return WorkflowRead.model_validate(_get_workflow_or_404(db, workflow_id))


@router.post("/{workflow_id}/cancel", response_model=WorkflowRead)
def cancel_workflow(
    workflow_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
) -> WorkflowRead:
    workflow = _get_workflow_or_404(db, workflow_id)
    workflow = engine.cancel_workflow(db, workflow)
    audit.record_audit(
        db,
        action="workflow.cancel",
        entity_type="workflow",
        entity_id=str(workflow.id),
        actor_id=user.id,
        actor_email=user.email,
        details=f"Cancelled workflow '{workflow.name}'",
    )
    return WorkflowRead.model_validate(workflow)


@router.post("/{workflow_id}/advance", response_model=WorkflowRead)
def advance_workflow(
    workflow_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_user),
) -> WorkflowRead:
    workflow = _get_workflow_or_404(db, workflow_id)
    timeout = get_settings().workflow_timeout_seconds
    try:
        workflow = engine.advance_workflow(db, workflow, timeout)
    except (engine.WorkflowCancelled, engine.WorkflowTimedOut) as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from None
    return WorkflowRead.model_validate(workflow)


@router.post("/{workflow_id}/recover", response_model=WorkflowRead)
def recover_workflow(
    workflow_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_user),
) -> WorkflowRead:
    workflow = _get_workflow_or_404(db, workflow_id)
    workflow = engine.recover_interrupted(db, workflow)
    return WorkflowRead.model_validate(workflow)


@router.post("/{workflow_id}/status", response_model=WorkflowRead)
def transition_workflow(
    workflow_id: int,
    payload: WorkflowTransition,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
) -> WorkflowRead:
    workflow = _get_workflow_or_404(db, workflow_id)
    updated = workflows.transition_workflow(db, workflow, payload.status, note=payload.note)
    audit.record_audit(
        db,
        action="workflow.status",
        entity_type="workflow",
        entity_id=str(updated.id),
        actor_id=user.id,
        actor_email=user.email,
        details=f"Workflow '{updated.name}' -> {payload.status}",
    )
    return WorkflowRead.model_validate(updated)


@router.post("/{workflow_id}/stages/{position}/status", response_model=WorkflowRead)
def transition_stage(
    workflow_id: int,
    position: int,
    payload: StageTransition,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
) -> WorkflowRead:
    workflow = _get_workflow_or_404(db, workflow_id)
    try:
        workflows.transition_stage(
            db, workflow, position, payload.status, error_message=payload.error_message
        )
    except workflows.WorkflowNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from None
    audit.record_audit(
        db,
        action="workflow.stage",
        entity_type="workflow",
        entity_id=str(workflow.id),
        actor_id=user.id,
        actor_email=user.email,
        details=f"Workflow '{workflow.name}' stage {position} -> {payload.status}",
    )
    return WorkflowRead.model_validate(workflow)