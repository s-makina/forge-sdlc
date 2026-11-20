"""Tool and skill registry services."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.registry import Skill, Tool
from app.schemas.registry import (
    SkillCreate,
    SkillUpdate,
    ToolCreate,
    ToolUpdate,
)


def list_tools(db: Session, *, include_inactive: bool = False) -> list[Tool]:
    stmt = select(Tool).order_by(Tool.name)
    if not include_inactive:
        stmt = stmt.where(Tool.is_active.is_(True))
    return list(db.scalars(stmt).all())


def get_tool(db: Session, tool_id: int) -> Tool | None:
    return db.get(Tool, tool_id)


def get_tool_by_name(db: Session, name: str) -> Tool | None:
    return db.scalar(select(Tool).where(Tool.name == name))


def create_tool(db: Session, payload: ToolCreate) -> Tool:
    existing = get_tool_by_name(db, payload.name)
    if existing is not None:
        raise ValueError(f"tool '{payload.name}' already exists")
    tool = Tool(
        name=payload.name,
        description=payload.description,
        input_schema=payload.input_schema,
        required_permissions=list(dict.fromkeys(payload.required_permissions)),
        is_active=payload.is_active,
    )
    db.add(tool)
    db.commit()
    db.refresh(tool)
    return tool


def update_tool(db: Session, tool: Tool, payload: ToolUpdate) -> Tool:
    updates = payload.model_dump(exclude_unset=True)
    if "required_permissions" in updates and updates["required_permissions"] is not None:
        updates["required_permissions"] = list(dict.fromkeys(updates["required_permissions"]))
    for field, value in updates.items():
        setattr(tool, field, value)
    db.commit()
    db.refresh(tool)
    return tool


def list_skills(db: Session, *, include_inactive: bool = False) -> list[Skill]:
    stmt = select(Skill).order_by(Skill.name)
    if not include_inactive:
        stmt = stmt.where(Skill.is_active.is_(True))
    return list(db.scalars(stmt).all())


def get_skill(db: Session, skill_id: int) -> Skill | None:
    return db.get(Skill, skill_id)


def get_skill_by_name(db: Session, name: str) -> Skill | None:
    return db.scalar(select(Skill).where(Skill.name == name))


def create_skill(db: Session, payload: SkillCreate) -> Skill:
    if get_skill_by_name(db, payload.name) is not None:
        raise ValueError(f"skill '{payload.name}' already exists")
    skill = Skill(
        name=payload.name,
        description=payload.description,
        instructions=payload.instructions,
        files=list(dict.fromkeys(payload.files)),
        is_active=payload.is_active,
    )
    db.add(skill)
    db.commit()
    db.refresh(skill)
    return skill


def update_skill(db: Session, skill: Skill, payload: SkillUpdate) -> Skill:
    updates = payload.model_dump(exclude_unset=True)
    if "files" in updates and updates["files"] is not None:
        updates["files"] = list(dict.fromkeys(updates["files"]))
    for field, value in updates.items():
        setattr(skill, field, value)
    db.commit()
    db.refresh(skill)
    return skill
