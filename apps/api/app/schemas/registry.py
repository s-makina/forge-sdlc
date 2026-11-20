"""Tool and skill registry schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ToolCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str = Field(min_length=1)
    input_schema: dict[str, Any] = {}
    required_permissions: list[str] = []
    is_active: bool = True


class ToolUpdate(BaseModel):
    description: str | None = Field(default=None, min_length=1)
    input_schema: dict[str, Any] | None = None
    required_permissions: list[str] | None = None
    is_active: bool | None = None


class ToolRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str
    input_schema: dict[str, Any]
    required_permissions: list[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime


class ToolList(BaseModel):
    items: list[ToolRead]
    total: int


class SkillCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str = Field(min_length=1)
    instructions: str | None = None
    files: list[str] = []
    is_active: bool = True


class SkillUpdate(BaseModel):
    description: str | None = Field(default=None, min_length=1)
    instructions: str | None = None
    files: list[str] | None = None
    is_active: bool | None = None


class SkillRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str
    instructions: str | None
    files: list[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime


class SkillList(BaseModel):
    items: list[SkillRead]
    total: int
