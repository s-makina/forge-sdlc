"""Execution API schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ExecutionCreate(BaseModel):
    project_id: int = Field(gt=0)
    task_id: str | None = Field(default=None, max_length=64)
    repository_url: str = Field(min_length=1, max_length=1024)
    branch: str = Field(default="main", max_length=255)
    image: str | None = Field(default=None, max_length=255)
    cpu_limit: float | None = Field(default=None, gt=0)
    memory_limit: str | None = Field(default=None, max_length=32)
    disk_limit: str | None = Field(default=None, max_length=32)
    timeout_seconds: int | None = Field(default=None, gt=0)
    network_policy: str | None = Field(default=None, max_length=32)


class ExecutionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    execution_id: str
    project_id: int
    task_id: str | None
    repository_url: str
    branch: str
    status: str
    container_id: str | None
    error_message: str | None
    image: str
    cpu_limit: float
    memory_limit: str
    disk_limit: str
    timeout_seconds: int
    network_policy: str
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None


class ExecutionList(BaseModel):
    items: list[ExecutionRead]
    total: int


class ExecutionStatusRead(BaseModel):
    execution_id: str
    status: str
    container_id: str | None
    error_message: str | None
    started_at: datetime | None
    finished_at: datetime | None


class ExecutionLogEntry(BaseModel):
    sequence: int
    timestamp: datetime
    level: str
    message: str


class ExecutionLogsRead(BaseModel):
    execution_id: str
    entries: list[ExecutionLogEntry]


class ExecutionArtefact(BaseModel):
    name: str
    location: str
    size_bytes: int


class ExecutionArtefactsRead(BaseModel):
    execution_id: str
    artefacts: list[ExecutionArtefact]


class ExecutionCancelRead(BaseModel):
    execution_id: str
    status: str
    requested: bool


class ExecutionCleanupRead(BaseModel):
    execution_id: str
    status: str
    cleaned: bool