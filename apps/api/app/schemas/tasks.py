"""Task and dependency schemas (Phase 4.3)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

TaskTypeValue = Literal[
    "feature", "bugfix", "refactoring", "dependency", "security", "performance", "testing", "documentation"
]
TaskPriorityValue = Literal["low", "medium", "high", "critical"]
TaskStatusValue = Literal[
    "draft", "ready", "assigned", "in_progress", "blocked", "review", "failed", "completed", "cancelled"
]


class DependencyRef(BaseModel):
    depends_on_id: int = Field(gt=0)


class TaskCreate(BaseModel):
    project_id: int = Field(gt=0)
    workflow_id: int | None = Field(default=None, gt=0)
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    task_type: TaskTypeValue = "feature"
    priority: TaskPriorityValue = "medium"
    acceptance_criteria: str | None = None
    repository_url: str | None = Field(default=None, max_length=1024)
    target_branch: str = Field(default="main", max_length=255)
    assigned_role: str | None = Field(default=None, max_length=128)
    assigned_agent_id: int | None = Field(default=None, gt=0)
    skills: list[str] = []
    model_profile: str | None = Field(default=None, max_length=64)
    relevant_files: list[str] = []
    cpu_limit: float | None = Field(default=None, gt=0)
    memory_limit: str | None = Field(default=None, max_length=32)
    disk_limit: str | None = Field(default=None, max_length=32)
    timeout_seconds: int | None = Field(default=None, gt=0)
    network_policy: str | None = Field(default=None, max_length=32)
    dependencies: list[int] = []

    @field_validator("skills", "relevant_files", "dependencies")
    @classmethod
    def _dedupe(cls, value: list) -> list:
        seen: set = set()
        out: list = []
        for item in value:
            if item not in seen:
                seen.add(item)
                out.append(item)
        return out


class TaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    task_type: TaskTypeValue | None = None
    priority: TaskPriorityValue | None = None
    status: TaskStatusValue | None = None
    acceptance_criteria: str | None = None
    repository_url: str | None = Field(default=None, max_length=1024)
    target_branch: str | None = Field(default=None, max_length=255)
    assigned_role: str | None = Field(default=None, max_length=128)
    assigned_agent_id: int | None = Field(default=None, gt=0)
    skills: list[str] | None = None
    model_profile: str | None = Field(default=None, max_length=64)
    relevant_files: list[str] | None = None
    result_summary: str | None = None
    artefact_refs: list[str] | None = None


class TaskRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    workflow_id: int | None
    title: str
    description: str | None
    task_type: str
    priority: str
    status: str
    acceptance_criteria: str | None
    repository_url: str | None
    target_branch: str
    assigned_role: str | None
    assigned_agent_id: int | None
    skills: list[str]
    model_profile: str | None
    relevant_files: list[str]
    cpu_limit: float | None
    memory_limit: str | None
    disk_limit: str | None
    timeout_seconds: int | None
    network_policy: str | None
    result_summary: str | None
    artefact_refs: list[str]
    dependencies: list[int] = []
    depends_on: list[int] = []
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime
    updated_at: datetime


class TaskList(BaseModel):
    items: list[TaskRead]
    total: int


class TaskStatusTransition(BaseModel):
    status: TaskStatusValue
    note: str | None = None


class SetDependencies(BaseModel):
    depends_on: list[int] = []