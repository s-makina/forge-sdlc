"""Agent registry: request and response schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

AgentVersionStatus = Literal["draft", "candidate", "active", "retired"]


class SkillRefRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    skill_name: str
    position: int


class ToolPermissionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    tool_name: str
    permissions: dict[str, bool]
    position: int


class AgentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    slug: str
    name: str
    role: str
    description: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class AgentVersionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    agent_id: int
    version: str
    status: AgentVersionStatus
    instructions: str
    capabilities: list[str]
    model_profile: str
    quality_gates: list[str]
    skills: list[SkillRefRead] = []
    tool_permissions: list[ToolPermissionRead] = []
    definition_hash: str | None
    source: str
    activated_at: datetime | None
    retired_at: datetime | None
    created_at: datetime
    updated_at: datetime


class AgentDetail(AgentRead):
    versions: list[AgentVersionRead] = []


class AgentList(BaseModel):
    items: list[AgentRead]
    total: int


class AgentVersionList(BaseModel):
    items: list[AgentVersionRead]
    total: int


class AgentCreate(BaseModel):
    """Create an agent with its first version.

    All configuration is supplied exactly as for a new version; there is no way
    to create an agent without a version.
    """

    slug: str = Field(min_length=1, max_length=255, pattern=r"^[a-z0-9][a-z0-9-_]*$")
    name: str = Field(min_length=1, max_length=255)
    role: str = Field(min_length=1, max_length=128)
    description: str | None = None
    instructions: str = Field(min_length=1)
    capabilities: list[str] = []
    model_profile: str = Field(min_length=1, max_length=64)
    quality_gates: list[str] = []
    skills: list[str] = []
    tools: list[str] = []

    @field_validator("capabilities", "quality_gates", "skills", "tools")
    @classmethod
    def _dedupe(cls, value: list[str]) -> list[str]:
        seen: set[str] = set()
        out: list[str] = []
        for item in value:
            if item not in seen:
                seen.add(item)
                out.append(item)
        return out


class AgentUpdate(BaseModel):
    """Update an agent. A change to any configuration field creates a new version.

    ``name``, ``role`` and ``description`` are mutable on the identity without a
    new version. Any of ``instructions``/``capabilities``/``model_profile``/
    ``quality_gates``/``skills``/``tools`` triggers creation of a new candidate
    version capturing the merged configuration.
    """

    name: str | None = Field(default=None, min_length=1, max_length=255)
    role: str | None = Field(default=None, min_length=1, max_length=128)
    description: str | None = None
    is_active: bool | None = None
    instructions: str | None = Field(default=None, min_length=1)
    capabilities: list[str] | None = None
    model_profile: str | None = Field(default=None, min_length=1, max_length=64)
    quality_gates: list[str] | None = None
    skills: list[str] | None = None
    tools: list[str] | None = None


class AgentVersionCreate(BaseModel):
    """Create a new immutable version for an existing agent."""

    instructions: str = Field(min_length=1)
    capabilities: list[str] = []
    model_profile: str = Field(min_length=1, max_length=64)
    quality_gates: list[str] = []
    skills: list[str] = []
    tools: list[str] = []
    source: str = "api"


class AgentVersionAction(BaseModel):
    """Promote, activate or retire an agent version."""

    action: Literal["promote", "activate", "retire"]
    note: str | None = None


class AgentYamlImport(BaseModel):
    """Import an agent version from a YAML definition document."""

    definition: str = Field(min_length=1)
    yaml_path: str | None = None


class AgentYamlImportResult(BaseModel):
    agent_id: int
    slug: str
    version: AgentVersionRead
    created_agent: bool
    created_version: bool


class ValidationIssue(BaseModel):
    path: str
    message: str


class ValidationReport(BaseModel):
    valid: bool
    errors: list[ValidationIssue] = []
    warnings: list[ValidationIssue] = []
    normalized: dict[str, Any] | None = None
