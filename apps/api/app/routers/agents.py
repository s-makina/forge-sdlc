"""Agent registry routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.deps.auth import require_user
from app.models.agent import Agent, AgentVersion
from app.models.user import User
from app.schemas.agents import (
    AgentCreate,
    AgentDetail,
    AgentList,
    AgentRead,
    AgentUpdate,
    AgentVersionAction,
    AgentVersionCreate,
    AgentVersionList,
    AgentVersionRead,
    AgentYamlImport,
    AgentYamlImportResult,
    ValidationReport,
)
from app.services import agent_registry, audit
from app.services.agent_definition import parse_definition

router = APIRouter(prefix="/agents", tags=["agents"])


def _get_agent_or_404(db: Session, agent_id: int) -> Agent:
    agent = agent_registry.get_agent(db, agent_id)
    if agent is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    return agent


def _get_version_or_404(db: Session, version_id: int) -> AgentVersion:
    version = agent_registry.get_version(db, version_id)
    if version is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent version not found")
    return version


def _handle_registry_error(exc: agent_registry.RegistryValidationError) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail={
            "code": "unknown_registry_reference",
            "message": "Agent references unknown capabilities, tools or skills",
            "details": [issue.model_dump() for issue in exc.issues],
        },
    )


@router.get("", response_model=AgentList)
def list_agents(
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    _: User = Depends(require_user),
) -> AgentList:
    items = agent_registry.list_agents(db, include_inactive=include_inactive)
    return AgentList(items=[AgentRead.model_validate(a) for a in items], total=len(items))


@router.post("", response_model=AgentDetail, status_code=status.HTTP_201_CREATED)
def create_agent(
    payload: AgentCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
) -> AgentDetail:
    try:
        agent = agent_registry.create_agent(db, payload)
    except agent_registry.RegistryValidationError as exc:
        raise _handle_registry_error(exc) from exc
    except agent_registry.VersionConflict as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    audit.record_audit(
        db,
        action="agent.create",
        entity_type="agent",
        entity_id=str(agent.id),
        actor_id=user.id,
        actor_email=user.email,
        details=f"Created agent '{agent.slug}'",
    )
    return AgentDetail.model_validate(agent)


@router.post("/import", response_model=AgentYamlImportResult, status_code=status.HTTP_201_CREATED)
def import_agent(
    payload: AgentYamlImport,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
) -> AgentYamlImportResult:
    definition, report, _ = parse_definition(payload.definition)
    if definition is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "invalid_definition",
                "message": "Agent definition failed validation",
                "details": [issue.model_dump() for issue in report.errors],
            },
        )
    try:
        agent, version, created_agent, created_version = agent_registry.import_definition(
            db, definition, yaml_path=payload.yaml_path
        )
    except agent_registry.RegistryValidationError as exc:
        raise _handle_registry_error(exc) from exc
    audit.record_audit(
        db,
        action="agent.import",
        entity_type="agent",
        entity_id=str(agent.id),
        actor_id=user.id,
        actor_email=user.email,
        details=f"Imported definition '{definition.id}' version '{version.version}'",
    )
    return AgentYamlImportResult(
        agent_id=agent.id,
        slug=agent.slug,
        version=AgentVersionRead.model_validate(version),
        created_agent=created_agent,
        created_version=created_version,
    )


@router.get("/{agent_id}", response_model=AgentDetail)
def get_agent(
    agent_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_user),
) -> AgentDetail:
    return AgentDetail.model_validate(_get_agent_or_404(db, agent_id))


@router.patch("/{agent_id}", response_model=AgentDetail)
def update_agent(
    agent_id: int,
    payload: AgentUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
) -> AgentDetail:
    agent = _get_agent_or_404(db, agent_id)
    try:
        updated = agent_registry.update_agent(db, agent, payload)
    except agent_registry.RegistryValidationError as exc:
        raise _handle_registry_error(exc) from exc
    audit.record_audit(
        db,
        action="agent.update",
        entity_type="agent",
        entity_id=str(updated.id),
        actor_id=user.id,
        actor_email=user.email,
        details=f"Updated agent '{updated.slug}'",
    )
    return AgentDetail.model_validate(updated)


@router.get("/{agent_id}/versions", response_model=AgentVersionList)
def list_versions(
    agent_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_user),
) -> AgentVersionList:
    agent = _get_agent_or_404(db, agent_id)
    items = [AgentVersionRead.model_validate(v) for v in agent.versions]
    return AgentVersionList(items=items, total=len(items))


@router.post(
    "/{agent_id}/versions",
    response_model=AgentVersionRead,
    status_code=status.HTTP_201_CREATED,
)
def create_version(
    agent_id: int,
    payload: AgentVersionCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
) -> AgentVersionRead:
    agent = _get_agent_or_404(db, agent_id)
    try:
        version = agent_registry.create_version(db, agent, payload)
    except agent_registry.RegistryValidationError as exc:
        raise _handle_registry_error(exc) from exc
    audit.record_audit(
        db,
        action="agent.version.create",
        entity_type="agent_version",
        entity_id=str(version.id),
        actor_id=user.id,
        actor_email=user.email,
        details=f"Created version '{version.version}' of agent '{agent.slug}'",
    )
    return AgentVersionRead.model_validate(version)


@router.post("/versions/{version_id}/action", response_model=AgentVersionRead)
def apply_version_action(
    version_id: int,
    payload: AgentVersionAction,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
) -> AgentVersionRead:
    version = _get_version_or_404(db, version_id)
    try:
        if payload.action == "promote":
            updated = agent_registry.promote_version(db, version)
        elif payload.action == "activate":
            updated = agent_registry.activate_version(db, version)
        else:
            updated = agent_registry.retire_version(db, version)
    except agent_registry.VersionConflict as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    audit.record_audit(
        db,
        action=f"agent.version.{payload.action}",
        entity_type="agent_version",
        entity_id=str(updated.id),
        actor_id=user.id,
        actor_email=user.email,
        details=f"{payload.action.capitalize()} agent version '{updated.version}'",
    )
    return AgentVersionRead.model_validate(updated)


@router.post("/validate", response_model=ValidationReport)
def validate_definition(payload: AgentYamlImport) -> ValidationReport:
    definition, report, _ = parse_definition(payload.definition)
    if definition is not None:
        report.normalized = definition.model_dump()
    return report
