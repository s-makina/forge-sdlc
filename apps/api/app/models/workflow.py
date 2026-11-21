"""Workflow template ORM models (Phase 4.2).

A workflow template is a reusable, ordered sequence of stages (README §10.2).
Each template carries a name/description, its category (feature, bugfix, ...),
and a ``stages`` list where each stage names an agent role and its optional
dependency stages. Instances of a workflow are created from a template with
typed inputs.
"""

from __future__ import annotations

from enum import StrEnum

from sqlalchemy import Boolean, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.base import TimestampMixin


class WorkflowTemplateCategory(StrEnum):
    """Categories of reusable workflow templates."""

    FEATURE = "feature"
    BUGFIX = "bugfix"
    REFACTORING = "refactoring"
    SETUP = "setup"
    DEPENDENCY = "dependency"
    SECURITY = "security"
    PERFORMANCE = "performance"
    TESTING = "testing"
    DOCUMENTATION = "documentation"
    MAINTENANCE = "maintenance"


class WorkflowTemplate(Base, TimestampMixin):
    __tablename__ = "workflow_templates"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    category: Mapped[str] = mapped_column(
        String(32), nullable=False, server_default=WorkflowTemplateCategory.FEATURE.value
    )
    input_schema: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    stages: Mapped[list["WorkflowStage"]] = relationship(
        back_populates="template",
        cascade="all, delete-orphan",
        order_by="WorkflowStage.position",
    )


class WorkflowStage(Base):
    __tablename__ = "workflow_stages"
    __table_args__ = (
        UniqueConstraint("template_id", "position", name="uq_workflow_stages_position"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    template_id: Mapped[int] = mapped_column(
        ForeignKey("workflow_templates.id"), nullable=False, index=True
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    agent_role: Mapped[str] = mapped_column(String(128), nullable=False)
    depends_on: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)

    template: Mapped[WorkflowTemplate] = relationship(back_populates="stages")