"""Model gateway schemas: providers, models, profiles, health and usage."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator, model_validator

from app.models.capabilities import ModelCapability

ProviderTypeLiteral = Literal["ollama", "openai-compatible"]
CheckStatusLiteral = Literal["ok", "error", "unknown"]


def _valid_capabilities(value: list[str]) -> list[str]:
    known = {c.value for c in ModelCapability}
    unknown = sorted(set(value) - known)
    if unknown:
        raise ValueError(f"unknown capabilities: {', '.join(unknown)}")
    return list(dict.fromkeys(value))


class ModelProviderCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    provider_type: ProviderTypeLiteral
    base_url: str = Field(min_length=1, max_length=1024)
    credential_ref: str | None = Field(default=None, max_length=255)
    api_key: SecretStr | None = Field(default=None, min_length=1, max_length=4096)
    timeout_seconds: int = Field(default=60, ge=1, le=600)
    is_active: bool = True

    @field_validator("base_url")
    @classmethod
    def _strip_base_url(cls, value: str) -> str:
        return value.strip().rstrip("/")

    @field_validator("credential_ref")
    @classmethod
    def _check_credential_ref(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            return None
        if not normalized.startswith("env:"):
            raise ValueError("credential_ref must use the 'env:NAME' reference form")
        return normalized

    @model_validator(mode="after")
    def _credential_source(self) -> ModelProviderCreate:
        if (
            self.api_key is not None
            and self.credential_ref is not None
            and bool(self.api_key.get_secret_value())
        ):
            raise ValueError("provide api_key or credential_ref, not both")
        return self


class ModelProviderUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    base_url: str | None = Field(default=None, min_length=1, max_length=1024)
    credential_ref: str | None = Field(default=None, max_length=255)
    api_key: SecretStr | None = Field(default=None, min_length=1, max_length=4096)
    clear_api_key: bool = False
    timeout_seconds: int | None = Field(default=None, ge=1, le=600)
    is_active: bool | None = None

    @field_validator("base_url")
    @classmethod
    def _strip_base_url(cls, value: str | None) -> str | None:
        return value.strip().rstrip("/") if value is not None else None

    @field_validator("credential_ref")
    @classmethod
    def _check_credential_ref(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            return None
        if not normalized.startswith("env:"):
            raise ValueError("credential_ref must use the 'env:NAME' reference form")
        return normalized

    @model_validator(mode="after")
    def _credential_source(self) -> ModelProviderUpdate:
        if (
            self.api_key is not None
            and self.credential_ref is not None
            and bool(self.api_key.get_secret_value())
        ):
            raise ValueError("provide api_key or credential_ref, not both")
        if (
            self.api_key is not None
            and self.clear_api_key
            and bool(self.api_key.get_secret_value())
        ):
            raise ValueError("api_key and clear_api_key cannot both be provided")
        return self


class ModelProviderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    provider_type: str
    base_url: str
    credential_ref: str | None
    has_api_key: bool = False
    timeout_seconds: int
    is_active: bool
    created_at: datetime
    updated_at: datetime


class ModelProviderList(BaseModel):
    items: list[ModelProviderRead]
    total: int


class ModelCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    display_name: str | None = Field(default=None, max_length=255)
    capabilities: list[str] = []
    context_window: int | None = Field(default=None, ge=1)
    input_cost_per_million: float | None = Field(default=None, ge=0)
    output_cost_per_million: float | None = Field(default=None, ge=0)
    is_active: bool = True

    @field_validator("capabilities")
    @classmethod
    def _caps(cls, value: list[str]) -> list[str]:
        return _valid_capabilities(value)


class ModelUpdate(BaseModel):
    display_name: str | None = Field(default=None, max_length=255)
    capabilities: list[str] | None = None
    context_window: int | None = Field(default=None, ge=1)
    input_cost_per_million: float | None = Field(default=None, ge=0)
    output_cost_per_million: float | None = Field(default=None, ge=0)
    is_active: bool | None = None

    @field_validator("capabilities")
    @classmethod
    def _caps(cls, value: list[str] | None) -> list[str] | None:
        return _valid_capabilities(value) if value is not None else None


class ModelRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    provider_id: int
    provider_name: str | None = None
    name: str
    display_name: str | None
    capabilities: list[str]
    context_window: int | None
    input_cost_per_million: float | None
    output_cost_per_million: float | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class ModelList(BaseModel):
    items: list[ModelRead]
    total: int


class ModelProfileCreate(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    description: str | None = None
    primary_model_id: int | None = None
    fallback_model_ids: list[int] = []
    required_capabilities: list[str] = []
    is_active: bool = True

    @field_validator("required_capabilities")
    @classmethod
    def _caps(cls, value: list[str]) -> list[str]:
        return _valid_capabilities(value)


class ModelProfileUpdate(BaseModel):
    description: str | None = None
    primary_model_id: int | None = None
    fallback_model_ids: list[int] | None = None
    required_capabilities: list[str] | None = None
    is_active: bool | None = None

    @field_validator("required_capabilities")
    @classmethod
    def _caps(cls, value: list[str] | None) -> list[str] | None:
        return _valid_capabilities(value) if value is not None else None


class ModelProfileRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
    primary_model_id: int | None
    fallback_model_ids: list[int]
    required_capabilities: list[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime


class ProviderCheckRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    provider_id: int
    model_id: int | None
    kind: str
    capability: str | None
    status: str
    latency_ms: float | None
    detail: str | None
    created_at: datetime


class CapabilityResult(BaseModel):
    capability: str
    supported: bool | None
    detail: str | None = None


class ConnectivityResult(BaseModel):
    ok: bool
    latency_ms: float | None = None
    detail: str | None = None


class ProviderHealth(BaseModel):
    provider_id: int
    provider_name: str
    provider_type: str
    base_url: str
    status: str
    connectivity: ConnectivityResult
    capabilities: dict[str, CapabilityResult] = {}
    checked_at: datetime
    model_count: int = 0


class HealthSummary(BaseModel):
    items: list[ProviderHealth]
    total: int


class ProfileResolutionRead(BaseModel):
    profile: str
    required_capabilities: list[str]
    model: ModelRead
    provider: ModelProviderRead
    used_fallback: bool


class UsageCreate(BaseModel):
    provider_id: int | None = None
    model_id: int | None = None
    profile_name: str | None = Field(default=None, max_length=64)
    agent_version_id: int | None = None
    input_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)
    total_tokens: int | None = Field(default=None, ge=0)
    cost_usd: float | None = Field(default=None, ge=0)
    success: bool = True
    latency_ms: float | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def _fill_total(self) -> UsageCreate:
        if self.total_tokens is None:
            self.total_tokens = self.input_tokens + self.output_tokens
        return self


class UsageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    provider_id: int | None
    model_id: int | None
    profile_name: str | None
    agent_version_id: int | None
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cost_usd: float | None
    success: bool
    latency_ms: float | None
    created_at: datetime


class UsageSummary(BaseModel):
    total_calls: int
    input_tokens: int
    output_tokens: int
    total_tokens: int
    total_cost_usd: float
    items: list[UsageRead] = []


class UsageList(BaseModel):
    items: list[UsageRead]
    total: int


class CapabilityItem(BaseModel):
    value: str
    description: str


class ModelCapabilitiesRead(BaseModel):
    items: list[CapabilityItem]


class GatewayConfigRead(BaseModel):
    generated_at: datetime
    model_count: int
    config: dict[str, Any]


class GatewayConfigApplyResult(BaseModel):
    written: bool
    path: str
    model_count: int
    reloaded: bool = False
    generated_at: datetime



class ModelProfileList(BaseModel):
    items: list[ModelProfileRead]
    total: int


class ProviderCheckList(BaseModel):
    items: list[ProviderCheckRead]
    total: int
