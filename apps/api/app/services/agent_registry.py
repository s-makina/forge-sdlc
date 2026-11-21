"""Agent registry service.

Agents have a stable identity (``Agent``) and immutable configuration revisions
(``AgentVersion``). Any change to configuration creates a new version rather than
overwriting the active one (README 8.5). Versions follow a promotion path:

    draft -> candidate -> active -> retired
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.models.agent import Agent, AgentSkill, AgentStatus, AgentToolPermission, AgentVersion
from app.models.capabilities import AgentCapability
from app.models.registry import Skill, Tool
from app.schemas.agents import AgentCreate, AgentUpdate, AgentVersionCreate, ValidationIssue
from app.services.agent_definition import AgentDefinition, definition_hash


class AgentNotFound(LookupError):
    pass


class VersionNotFound(LookupError):
    pass


class RegistryValidationError(ValueError):
    def __init__(self, issues: list[ValidationIssue]) -> None:
        self.issues = issues
        super().__init__("; ".join(f"{i.path}: {i.message}" for i in issues))


class VersionConflict(ValueError):
    pass


def list_agents(db: Session, *, include_inactive: bool = False) -> list[Agent]:
    stmt = select(Agent).order_by(Agent.name)
    if not include_inactive:
        stmt = stmt.where(Agent.is_active.is_(True))
    return list(db.scalars(stmt).all())


def get_agent(db: Session, agent_id: int) -> Agent | None:
    stmt = (
        select(Agent)
        .where(Agent.id == agent_id)
        .options(
            selectinload(Agent.versions).selectinload(AgentVersion.skills),
            selectinload(Agent.versions).selectinload(AgentVersion.tool_permissions),
        )
    )
    return db.scalar(stmt)


def get_agent_by_slug(db: Session, slug: str) -> Agent | None:
    stmt = (
        select(Agent)
        .where(Agent.slug == slug)
        .options(
            selectinload(Agent.versions).selectinload(AgentVersion.skills),
            selectinload(Agent.versions).selectinload(AgentVersion.tool_permissions),
        )
    )
    return db.scalar(stmt)


def get_version(db: Session, version_id: int) -> AgentVersion | None:
    stmt = (
        select(AgentVersion)
        .where(AgentVersion.id == version_id)
        .options(
            selectinload(AgentVersion.skills),
            selectinload(AgentVersion.tool_permissions),
        )
    )
    return db.scalar(stmt)


def latest_version(db: Session, agent_id: int) -> AgentVersion | None:
    stmt = (
        select(AgentVersion)
        .where(AgentVersion.agent_id == agent_id)
        .order_by(AgentVersion.id.desc())
        .options(
            selectinload(AgentVersion.skills),
            selectinload(AgentVersion.tool_permissions),
        )
        .limit(1)
    )
    return db.scalar(stmt)


def active_version(db: Session, agent_id: int) -> AgentVersion | None:
    stmt = select(AgentVersion).where(
        AgentVersion.agent_id == agent_id,
        AgentVersion.status == AgentStatus.ACTIVE.value,
    )
    return db.scalar(stmt)


def _next_version(db: Session, agent_id: int) -> str:
    count = int(
        db.scalar(select(func.count()).select_from(AgentVersion).where(AgentVersion.agent_id == agent_id))
        or 0
    )
    return f"1.0.{count}"


def validate_config(
    db: Session,
    *,
    capabilities: list[str],
    tools: list[str],
    skills: list[str],
) -> None:
    issues: list[ValidationIssue] = []
    known = {c.value for c in AgentCapability}
    for capability in capabilities:
        if capability not in known:
            issues.append(
                ValidationIssue(path="capabilities", message=f"unknown capability '{capability}'")
            )
    for tool_name in tools:
        if db.scalar(select(Tool).where(Tool.name == tool_name, Tool.is_active.is_(True))) is None:
            issues.append(ValidationIssue(path="tools", message=f"unknown tool '{tool_name}'"))
    for skill_name in skills:
        if (
            db.scalar(select(Skill).where(Skill.name == skill_name, Skill.is_active.is_(True)))
            is None
        ):
            issues.append(ValidationIssue(path="skills", message=f"unknown skill '{skill_name}'"))
    if issues:
        raise RegistryValidationError(issues)


def _tool_required_permissions(db: Session, tool_name: str) -> list[str]:
    row = db.scalar(select(Tool).where(Tool.name == tool_name, Tool.is_active.is_(True)))
    if row is None:
        return []
    return list(row.required_permissions)


def _tool_permission_slice(
    required_permissions: list[str], permissions: dict[str, bool]
) -> dict[str, bool]:
    return {
        key: value
        for key, value in permissions.items()
        if key in required_permissions
    }


def _build_version(
    db: Session,
    *,
    agent: Agent,
    version: str,
    instructions: str,
    capabilities: list[str],
    model_profile: str,
    quality_gates: list[str],
    skills: list[str],
    tools: list[str],
    permissions: dict[str, bool] | None = None,
    status: AgentStatus = AgentStatus.CANDIDATE,
    source: str = "api",
    definition_hash_value: str | None = None,
) -> AgentVersion:
    permission_map = permissions or {}
    row = AgentVersion(
        agent_id=agent.id,
        version=version,
        status=status.value,
        instructions=instructions,
        capabilities=list(dict.fromkeys(capabilities)),
        model_profile=model_profile,
        quality_gates=list(dict.fromkeys(quality_gates)),
        source=source,
        definition_hash=definition_hash_value,
    )
    for position, skill_name in enumerate(dict.fromkeys(skills)):
        row.skills.append(AgentSkill(skill_name=skill_name, position=position))
    for position, tool_name in enumerate(dict.fromkeys(tools)):
        required = _tool_required_permissions(db, tool_name)
        row.tool_permissions.append(
            AgentToolPermission(
                tool_name=tool_name,
                permissions=_tool_permission_slice(required, permission_map),
                position=position,
            )
        )
    return row


def create_agent(db: Session, payload: AgentCreate) -> Agent:
    if db.scalar(select(Agent).where(Agent.slug == payload.slug)) is not None:
        raise VersionConflict(f"agent '{payload.slug}' already exists")
    validate_config(
        db,
        capabilities=payload.capabilities,
        tools=payload.tools,
        skills=payload.skills,
    )
    agent = Agent(
        slug=payload.slug,
        name=payload.name,
        role=payload.role,
        description=payload.description,
        is_active=True,
    )
    db.add(agent)
    try:
        db.flush()
        version = _build_version(
            db=db,
            agent=agent,
            version="1.0.0",
            instructions=payload.instructions,
            capabilities=payload.capabilities,
            model_profile=payload.model_profile,
            quality_gates=payload.quality_gates,
            skills=payload.skills,
            tools=payload.tools,
            status=AgentStatus.CANDIDATE,
        )
        db.add(version)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise VersionConflict(f"agent '{payload.slug}' already exists") from None
    refreshed = get_agent(db, agent.id)
    assert refreshed is not None
    return refreshed


def update_agent(db: Session, agent: Agent, payload: AgentUpdate) -> Agent:
    updates = payload.model_dump(exclude_unset=True)

    identity_changed = False
    for field in ("name", "role", "description", "is_active"):
        if field in updates:
            setattr(agent, field, updates[field])
            identity_changed = True

    config_fields = ("instructions", "capabilities", "model_profile", "quality_gates")
    list_fields = ("skills", "tools")
    config_changed = any(field in updates for field in config_fields + list_fields)

    if not config_changed:
        db.commit()
        if identity_changed:
            db.refresh(agent)
        return agent

    previous = latest_version(db, agent.id)
    instructions = updates.get("instructions", previous.instructions if previous else None)
    model_profile = updates.get("model_profile", previous.model_profile if previous else None)
    if not instructions or not model_profile:
        raise RegistryValidationError(
            [
                ValidationIssue(
                    path="instructions",
                    message="instructions and model_profile are required",
                )
            ]
        )

    capabilities = list(
        updates.get("capabilities", list(previous.capabilities) if previous else []) or []
    )
    quality_gates = list(
        updates.get("quality_gates", list(previous.quality_gates) if previous else []) or []
    )
    skills = list(
        updates.get(
            "skills",
            [s.skill_name for s in previous.skills] if previous else [],
        )
        or []
    )
    tools = list(
        updates.get(
            "tools",
            [t.tool_name for t in previous.tool_permissions] if previous else [],
        )
        or []
    )

    validate_config(db, capabilities=capabilities, tools=tools, skills=skills)

    version = _build_version(
        db=db,
        agent=agent,
        version=_next_version(db, agent.id),
        instructions=str(instructions),
        capabilities=capabilities,
        model_profile=str(model_profile),
        quality_gates=quality_gates,
        skills=skills,
        tools=tools,
        status=AgentStatus.CANDIDATE,
    )
    db.add(version)
    db.commit()
    db.expire(agent, ["versions"])
    refreshed = get_agent(db, agent.id)
    assert refreshed is not None
    return refreshed


def create_version(db: Session, agent: Agent, payload: AgentVersionCreate) -> AgentVersion:
    validate_config(
        db,
        capabilities=payload.capabilities,
        tools=payload.tools,
        skills=payload.skills,
    )
    version = _build_version(
        db=db,
        agent=agent,
        version=_next_version(db, agent.id),
        instructions=payload.instructions,
        capabilities=payload.capabilities,
        model_profile=payload.model_profile,
        quality_gates=payload.quality_gates,
        skills=payload.skills,
        tools=payload.tools,
        status=AgentStatus.CANDIDATE,
        source=payload.source,
    )
    db.add(version)
    db.commit()
    db.refresh(version)
    return version


def promote_version(db: Session, version: AgentVersion) -> AgentVersion:
    if version.status != AgentStatus.DRAFT.value:
        raise VersionConflict(f"only draft versions can be promoted (status={version.status})")
    version.status = AgentStatus.CANDIDATE.value
    db.commit()
    db.refresh(version)
    return version


def activate_version(db: Session, version: AgentVersion) -> AgentVersion:
    if version.status != AgentStatus.CANDIDATE.value:
        raise VersionConflict(f"only candidate versions can be activated (status={version.status})")
    now = datetime.now(UTC)
    siblings = list(
        db.scalars(
            select(AgentVersion).where(
                AgentVersion.agent_id == version.agent_id,
                AgentVersion.id != version.id,
                AgentVersion.status == AgentStatus.ACTIVE.value,
            )
        ).all()
    )
    for sibling in siblings:
        sibling.status = AgentStatus.RETIRED.value
        sibling.retired_at = now
    version.status = AgentStatus.ACTIVE.value
    version.activated_at = now
    version.retired_at = None
    db.commit()
    db.refresh(version)
    return version


def retire_version(db: Session, version: AgentVersion) -> AgentVersion:
    if version.status != AgentStatus.ACTIVE.value:
        raise VersionConflict(f"only active versions can be retired (status={version.status})")
    version.status = AgentStatus.RETIRED.value
    version.retired_at = datetime.now(UTC)
    db.commit()
    db.refresh(version)
    return version


def import_definition(
    db: Session, definition: AgentDefinition, *, yaml_path: str | None = None
) -> tuple[Agent, AgentVersion, bool, bool]:
    validate_config(
        db,
        capabilities=definition.capabilities,
        tools=definition.tools,
        skills=definition.skills,
    )

    created_agent = False
    agent = get_agent_by_slug(db, definition.id)
    if agent is None:
        agent = Agent(
            slug=definition.id,
            name=definition.name,
            role=definition.role,
            description=f"Imported from {yaml_path}" if yaml_path else None,
            is_active=True,
        )
        db.add(agent)
        db.flush()
        created_agent = True

    digest = definition_hash(definition)
    previous = latest_version(db, agent.id)
    if previous is not None and previous.definition_hash == digest:
        existing = get_version(db, previous.id)
        assert existing is not None
        return agent, existing, created_agent, False

    version = _build_version(
        db=db,
        agent=agent,
        version=definition.version if previous is None else _next_version(db, agent.id),
        instructions=definition.instructions,
        capabilities=definition.capabilities,
        model_profile=definition.model_profile,
        quality_gates=definition.quality_gates,
        skills=definition.skills,
        tools=definition.tools,
        permissions=definition.permissions,
        status=AgentStatus.CANDIDATE,
        source="yaml",
        definition_hash_value=digest,
    )
    db.add(version)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise VersionConflict(
            f"agent '{definition.id}' version '{version.version}' already exists"
        ) from None
    db.expire(agent, ["versions"])
    refreshed = get_agent(db, agent.id)
    assert refreshed is not None
    stored = get_version(db, version.id)
    assert stored is not None
    return refreshed, stored, created_agent, True
