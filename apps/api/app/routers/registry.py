"""Tool and skill registry routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.deps.auth import require_user
from app.models.user import User
from app.schemas.registry import (
    SkillCreate,
    SkillList,
    SkillRead,
    SkillUpdate,
    ToolCreate,
    ToolList,
    ToolRead,
    ToolUpdate,
)
from app.services import audit, registry

router = APIRouter(prefix="/registries", tags=["registries"])


@router.get("/tools", response_model=ToolList)
def list_tools(
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    _: User = Depends(require_user),
) -> ToolList:
    items = registry.list_tools(db, include_inactive=include_inactive)
    return ToolList(items=[ToolRead.model_validate(t) for t in items], total=len(items))


@router.post("/tools", response_model=ToolRead, status_code=status.HTTP_201_CREATED)
def create_tool(
    payload: ToolCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
) -> ToolRead:
    try:
        tool = registry.create_tool(db, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    audit.record_audit(
        db,
        action="tool.create",
        entity_type="tool",
        entity_id=str(tool.id),
        actor_id=user.id,
        actor_email=user.email,
        details=f"Registered tool '{tool.name}'",
    )
    return ToolRead.model_validate(tool)


@router.get("/tools/{tool_id}", response_model=ToolRead)
def get_tool(
    tool_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_user),
) -> ToolRead:
    tool = registry.get_tool(db, tool_id)
    if tool is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tool not found")
    return ToolRead.model_validate(tool)


@router.patch("/tools/{tool_id}", response_model=ToolRead)
def update_tool(
    tool_id: int,
    payload: ToolUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
) -> ToolRead:
    tool = registry.get_tool(db, tool_id)
    if tool is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tool not found")
    updated = registry.update_tool(db, tool, payload)
    audit.record_audit(
        db,
        action="tool.update",
        entity_type="tool",
        entity_id=str(updated.id),
        actor_id=user.id,
        actor_email=user.email,
        details=f"Updated tool '{updated.name}'",
    )
    return ToolRead.model_validate(updated)


@router.get("/skills", response_model=SkillList)
def list_skills(
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    _: User = Depends(require_user),
) -> SkillList:
    items = registry.list_skills(db, include_inactive=include_inactive)
    return SkillList(items=[SkillRead.model_validate(s) for s in items], total=len(items))


@router.post("/skills", response_model=SkillRead, status_code=status.HTTP_201_CREATED)
def create_skill(
    payload: SkillCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
) -> SkillRead:
    try:
        skill = registry.create_skill(db, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    audit.record_audit(
        db,
        action="skill.create",
        entity_type="skill",
        entity_id=str(skill.id),
        actor_id=user.id,
        actor_email=user.email,
        details=f"Registered skill '{skill.name}'",
    )
    return SkillRead.model_validate(skill)


@router.get("/skills/{skill_id}", response_model=SkillRead)
def get_skill(
    skill_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_user),
) -> SkillRead:
    skill = registry.get_skill(db, skill_id)
    if skill is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Skill not found")
    return SkillRead.model_validate(skill)


@router.patch("/skills/{skill_id}", response_model=SkillRead)
def update_skill(
    skill_id: int,
    payload: SkillUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
) -> SkillRead:
    skill = registry.get_skill(db, skill_id)
    if skill is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Skill not found")
    updated = registry.update_skill(db, skill, payload)
    audit.record_audit(
        db,
        action="skill.update",
        entity_type="skill",
        entity_id=str(updated.id),
        actor_id=user.id,
        actor_email=user.email,
        details=f"Updated skill '{updated.name}'",
    )
    return SkillRead.model_validate(updated)
