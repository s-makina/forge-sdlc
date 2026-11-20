"""Agent registry ORM models: agents, immutable versions, skills and tools."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.base import TimestampMixin


class AgentStatus(StrEnum):
    """Lifecycle status of an agent version."""

    DRAFT = "draft"
    CANDIDATE = "candidate"
    ACTIVE = "active"
    RETIRED = "retired"


class Agent(Base, TimestampMixin):
    """A stable agent identity. Configuration lives in immutable versions."""

    __tablename__ = "agents"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="1")

    versions: Mapped[list[AgentVersion]] = relationship(
        back_populates="agent", cascade="all, delete-orphan", order_by="AgentVersion.id"
    )


class AgentVersion(Base, TimestampMixin):
    """An immutable configuration revision of an agent.

    A change to any configuration field creates a *new* row rather than updating
    an existing one. ``status`` follows the promotion path
    draft -> candidate -> active -> retired. At most one version per agent is
    ``active``; that invariant is enforced in the service and migration layers.
    """

    __tablename__ = "agent_versions"
    __table_args__ = (
        UniqueConstraint("agent_id", "version", name="uq_agent_versions_agent_version"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    agent_id: Mapped[int] = mapped_column(ForeignKey("agents.id"), nullable=False, index=True)
    version: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, server_default=AgentStatus.DRAFT.value, index=True
    )
    instructions: Mapped[str] = mapped_column(Text, nullable=False)
    capabilities: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    model_profile: Mapped[str] = mapped_column(String(64), nullable=False)
    quality_gates: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    definition_hash: Mapped[str | None] = mapped_column(String(64))
    source: Mapped[str] = mapped_column(String(32), nullable=False, server_default="yaml")
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    retired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    agent: Mapped[Agent] = relationship(back_populates="versions")
    skills: Mapped[list[AgentSkill]] = relationship(
        back_populates="version", cascade="all, delete-orphan"
    )
    tool_permissions: Mapped[list[AgentToolPermission]] = relationship(
        back_populates="version", cascade="all, delete-orphan"
    )


class AgentSkill(Base):
    """A skill (by registry name) that a specific agent version declares."""

    __tablename__ = "agent_skills"
    __table_args__ = (
        UniqueConstraint("agent_version_id", "skill_name", name="uq_agent_skills_version_name"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    agent_version_id: Mapped[int] = mapped_column(
        ForeignKey("agent_versions.id"), nullable=False, index=True
    )
    skill_name: Mapped[str] = mapped_column(String(255), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    version: Mapped[AgentVersion] = relationship(back_populates="skills")


class AgentToolPermission(Base):
    """A tool an agent version may use, with its declared permission flags.

    ``permissions`` is a JSON object of ``{permission_name: bool}`` entries as in
    the README 8.4 agent definition (e.g. ``{"write_repository": true}``).
    """

    __tablename__ = "agent_tool_permissions"
    __table_args__ = (
        UniqueConstraint("agent_version_id", "tool_name", name="uq_agent_tool_version_tool"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    agent_version_id: Mapped[int] = mapped_column(
        ForeignKey("agent_versions.id"), nullable=False, index=True
    )
    tool_name: Mapped[str] = mapped_column(String(255), nullable=False)
    permissions: Mapped[dict[str, bool]] = mapped_column(JSON, nullable=False, default=dict)
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    version: Mapped[AgentVersion] = relationship(back_populates="tool_permissions")
