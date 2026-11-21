"""Workflow template and instance schemas (Phase 4.2/4.7)."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

WorkflowCategoryValue = Literal[
    "feature", "bugfix", "refactoring", "setup", "dependency", "security", "performance", "testing", "documentation", "maintenance"
]
WorkflowStatusValue = Literal[
    "pending", "running", "waiting_approval", "succeeded", "failed", "cancelled"
]
StageStatusValue = Literal[
    "pending", "running", "succeeded", "failed", "cancelled"
]


class StageDefinition(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    agent_role: str = Field(min_length=1, max_length=128)
    depends_on: list[str] = []


class WorkflowTemplateCreate(BaseModel):
    slug: str = Field(min_length=1, max_length=64, pattern=r"^[a-z0-9][a-z0-9-_]*$")
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    category: WorkflowCategoryValue = "feature"
    input_schema: dict[str, Any] = {}
    stages: list[StageDefinition] = []


class WorkflowStageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    position: int
    name: str
    agent_role: str
    depends_on: list[str]


class WorkflowTemplateRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    slug: str
    name: str
    description: str | None
    category: str
    input_schema: dict[str, Any]
    is_active: bool
    stages: list[WorkflowStageRead] = []
    created_at: datetime
    updated_at: datetime


class WorkflowTemplateList(BaseModel):
    items: list[WorkflowTemplateRead]
    total: int


class WorkflowStageRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    workflow_id: int
    position: int
    name: str
    agent_role: str
    status: str
    retries: int
    error_message: str | None
    started_at: datetime | None
    finished_at: datetime | None


class WorkflowCreate(BaseModel):
    project_id: int = Field(gt=0)
    template_id: int = Field(gt=0)
    name: str = Field(min_length=1, max_length=255)
    inputs: dict[str, Any] = {}


class WorkflowRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    template_id: int
    name: str
    status: str
    inputs: dict[str, Any]
    error_message: str | None
    stages: list[WorkflowStageRunRead] = []
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime
    updated_at: datetime


class WorkflowList(BaseModel):
    items: list[WorkflowRead]
    total: int


class WorkflowTransition(BaseModel):
    status: WorkflowStatusValue
    note: str | None = None


class StageTransition(BaseModel):
    status: StageStatusValue
    error_message: str | None = None