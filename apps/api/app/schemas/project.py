"""Project and repository schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class RepositoryCreate(BaseModel):
    url: str = Field(min_length=1, max_length=1024)
    default_branch: str = Field(default="main", max_length=255)


class RepositoryUpdate(BaseModel):
    url: str | None = Field(default=None, min_length=1, max_length=1024)
    default_branch: str | None = Field(default=None, max_length=255)


class RepositoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    url: str
    default_branch: str
    adapter_status: str
    adapter_name: str | None
    is_active: bool
    created_at: datetime


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    default_branch: str = Field(default="main", max_length=255)
    repositories: list[RepositoryCreate] = []


class ProjectUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    default_branch: str | None = Field(default=None, max_length=255)
    is_active: bool | None = None


class ProjectRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
    default_branch: str
    is_active: bool
    created_at: datetime
    repositories: list[RepositoryRead] = []


class ProjectList(BaseModel):
    items: list[ProjectRead]
    total: int
