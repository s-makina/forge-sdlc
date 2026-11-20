"""Model provider, model, profile, health-check and usage ORM models."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.base import TimestampMixin


class ProviderType(StrEnum):
    """Supported provider families."""

    OLLAMA = "ollama"
    OPENAI_COMPATIBLE = "openai-compatible"


class CheckKind(StrEnum):
    """Kind of probe recorded in ``provider_checks``."""

    CONNECTIVITY = "connectivity"
    CAPABILITY = "capability"


class ModelProvider(Base, TimestampMixin):
    """A model endpoint plus a *reference* to its credential.

    Credentials are never stored here: ``credential_ref`` is an indirection such
    as ``env:OPENAI_API_KEY`` which the secret resolver turns into a value at call
    time, and which is redacted from every API response.
    """

    __tablename__ = "model_providers"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    provider_type: Mapped[str] = mapped_column(String(32), nullable=False)
    base_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    credential_ref: Mapped[str | None] = mapped_column(String(255))
    timeout_seconds: Mapped[int] = mapped_column(Integer, nullable=False, server_default="60")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="1")

    models: Mapped[list[Model]] = relationship(
        back_populates="provider", cascade="all, delete-orphan"
    )
    checks: Mapped[list[ProviderCheck]] = relationship(
        back_populates="provider", cascade="all, delete-orphan"
    )


class Model(Base, TimestampMixin):
    """A concrete model exposed by a provider with declared capabilities.

    ``capabilities`` is a list of :class:`app.models.capabilities.ModelCapability`
    values. ``context_window`` and the two cost columns are optional because
    providers do not always publish them.
    """

    __tablename__ = "models"
    __table_args__ = (UniqueConstraint("provider_id", "name", name="uq_models_provider_name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    provider_id: Mapped[int] = mapped_column(
        ForeignKey("model_providers.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(255))
    capabilities: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    context_window: Mapped[int | None] = mapped_column(Integer)
    input_cost_per_million: Mapped[float | None] = mapped_column(Float)
    output_cost_per_million: Mapped[float | None] = mapped_column(Float)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="1")

    provider: Mapped[ModelProvider] = relationship(back_populates="models")


class ModelProfile(Base, TimestampMixin):
    """A logical model name mapped to an ordered list of concrete models.

    ``primary_model_id`` is tried first; ``fallback_model_ids`` are considered in
    order and only ever used if they satisfy the same capability requirements.
    """

    __tablename__ = "model_profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text)
    primary_model_id: Mapped[int | None] = mapped_column(
        ForeignKey("models.id"), nullable=True, index=True
    )
    fallback_model_ids: Mapped[list[int]] = mapped_column(JSON, nullable=False, default=list)
    required_capabilities: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="1")

    primary_model: Mapped[Model | None] = relationship(foreign_keys=[primary_model_id])


class ProviderCheck(Base):
    """Recorded result of a health or capability probe against a provider/model."""

    __tablename__ = "provider_checks"

    id: Mapped[int] = mapped_column(primary_key=True)
    provider_id: Mapped[int] = mapped_column(
        ForeignKey("model_providers.id"), nullable=False, index=True
    )
    model_id: Mapped[int | None] = mapped_column(ForeignKey("models.id"), nullable=True)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    capability: Mapped[str | None] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    latency_ms: Mapped[float | None] = mapped_column(Float)
    detail: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    provider: Mapped[ModelProvider] = relationship(back_populates="checks")


class UsageRecord(Base):
    """A single model call's token/cost usage."""

    __tablename__ = "usage_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    provider_id: Mapped[int | None] = mapped_column(ForeignKey("model_providers.id"), index=True)
    model_id: Mapped[int | None] = mapped_column(ForeignKey("models.id"), index=True)
    profile_name: Mapped[str | None] = mapped_column(String(64), index=True)
    agent_version_id: Mapped[int | None] = mapped_column(
        ForeignKey("agent_versions.id"), nullable=True, index=True
    )
    input_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cost_usd: Mapped[float | None] = mapped_column(Float)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    latency_ms: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
