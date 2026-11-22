"""Model provider, model and profile services.

The router never silently routes to rev a model that an agent definition cannot
satisfy: :func:`resolve_profile` either returns a model that declares every
required capability, or raises :class:`RoutingError` explaining why. Fallbacks
can only be used when they are *at least* as capable as the primary.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.core.config import get_settings
from app.core.secrets import encrypt_credential
from app.models.capabilities import ModelCapability
from app.models.model_provider import Model, ModelProfile, ModelProvider
from app.schemas.models import (
    ModelCreate,
    ModelProfileCreate,
    ModelProfileUpdate,
    ModelProviderCreate,
    ModelProviderUpdate,
    ModelUpdate,
)


class ProviderNotFound(LookupError):
    pass


class ProfileNotFound(LookupError):
    pass


class DuplicateName(ValueError):
    pass


@dataclass(slots=True)
class RoutingError(ValueError):
    profile: str
    message: str

    def __str__(self) -> str:
        return f"cannot route profile '{self.profile}': {self.message}"


def list_providers(db: Session, *, include_inactive: bool = False) -> list[ModelProvider]:
    stmt = (
        select(ModelProvider)
        .options(selectinload(ModelProvider.models))
        .order_by(ModelProvider.name)
    )
    if not include_inactive:
        stmt = stmt.where(ModelProvider.is_active.is_(True))
    return list(db.scalars(stmt).all())


def get_provider(db: Session, provider_id: int) -> ModelProvider | None:
    stmt = (
        select(ModelProvider)
        .where(ModelProvider.id == provider_id)
        .options(selectinload(ModelProvider.models))
    )
    return db.scalar(stmt)


def create_provider(db: Session, payload: ModelProviderCreate) -> ModelProvider:
    if db.scalar(select(ModelProvider).where(ModelProvider.name == payload.name)) is not None:
        raise DuplicateName(f"provider '{payload.name}' already exists")
    raw_api_key = payload.api_key.get_secret_value() if payload.api_key is not None else None
    provider = ModelProvider(
        name=payload.name,
        provider_type=payload.provider_type,
        base_url=payload.base_url,
        credential_ref=payload.credential_ref,
        credential_ciphertext=(
            encrypt_credential(raw_api_key, get_settings().credential_encryption_key)
            if raw_api_key is not None
            else None
        ),
        timeout_seconds=payload.timeout_seconds,
        is_active=payload.is_active,
    )
    db.add(provider)
    db.commit()
    db.refresh(provider)
    return provider


def update_provider(
    db: Session, provider: ModelProvider, payload: ModelProviderUpdate
) -> ModelProvider:
    updates = payload.model_dump(exclude_unset=True, exclude={"api_key", "clear_api_key"})
    raw_api_key = payload.api_key.get_secret_value() if payload.api_key is not None else None
    if raw_api_key:
        updates["credential_ciphertext"] = encrypt_credential(
            raw_api_key, get_settings().credential_encryption_key
        )
        updates["credential_ref"] = None
    elif payload.clear_api_key:
        updates["credential_ciphertext"] = None
    if "credential_ref" in updates and updates["credential_ref"] is not None:
        updates["credential_ciphertext"] = None
        updates["credential_ref"] = updates["credential_ref"].strip() or None
    new_name = updates.get("name")
    if new_name is not None and new_name != provider.name:
        clash = db.scalar(
            select(ModelProvider).where(
                ModelProvider.name == new_name, ModelProvider.id != provider.id
            )
        )
        if clash is not None:
            raise DuplicateName(f"provider '{new_name}' already exists")
    for field, value in updates.items():
        setattr(provider, field, value)
    db.commit()
    db.refresh(provider)
    return provider


def get_model(db: Session, model_id: int) -> Model | None:
    stmt = (
        select(Model)
        .where(Model.id == model_id)
        .options(selectinload(Model.provider))
    )
    return db.scalar(stmt)


def list_models(db: Session, *, include_inactive: bool = False) -> list[Model]:
    stmt = select(Model).options(selectinload(Model.provider)).order_by(Model.name)
    if not include_inactive:
        stmt = stmt.where(Model.is_active.is_(True))
    return list(db.scalars(stmt).all())


def create_model(db: Session, provider: ModelProvider, payload: ModelCreate) -> Model:
    clash = db.scalar(
        select(Model).where(Model.provider_id == provider.id, Model.name == payload.name)
    )
    if clash is not None:
        raise DuplicateName(f"model '{payload.name}' already exists on provider '{provider.name}'")
    model = Model(
        provider_id=provider.id,
        name=payload.name,
        display_name=payload.display_name,
        capabilities=list(dict.fromkeys(payload.capabilities)),
        context_window=payload.context_window,
        input_cost_per_million=payload.input_cost_per_million,
        output_cost_per_million=payload.output_cost_per_million,
        is_active=payload.is_active,
    )
    db.add(model)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise DuplicateName(f"model '{payload.name}' already exists") from None
    db.refresh(model)
    return model


def update_model(db: Session, model: Model, payload: ModelUpdate) -> Model:
    updates = payload.model_dump(exclude_unset=True)
    if "capabilities" in updates and updates["capabilities"] is not None:
        updates["capabilities"] = list(dict.fromkeys(updates["capabilities"]))
    for field, value in updates.items():
        setattr(model, field, value)
    db.commit()
    db.refresh(model)
    return model


def list_profiles(db: Session) -> list[ModelProfile]:
    stmt = select(ModelProfile).order_by(ModelProfile.name)
    return list(db.scalars(stmt).all())


def get_profile(db: Session, profile_id: int) -> ModelProfile | None:
    return db.get(ModelProfile, profile_id)


def get_profile_by_name(db: Session, name: str) -> ModelProfile | None:
    return db.scalar(select(ModelProfile).where(ModelProfile.name == name))


def _validate_model_ids(db: Session, primary: int | None, fallbacks: list[int]) -> None:
    for model_id in ([primary] if primary is not None else []) + fallbacks:
        if db.get(Model, model_id) is None:
            raise ProviderNotFound(f"model {model_id} not found")


def create_profile(db: Session, payload: ModelProfileCreate) -> ModelProfile:
    if get_profile_by_name(db, payload.name) is not None:
        raise DuplicateName(f"profile '{payload.name}' already exists")
    _validate_model_ids(db, payload.primary_model_id, payload.fallback_model_ids)
    profile = ModelProfile(
        name=payload.name,
        description=payload.description,
        primary_model_id=payload.primary_model_id,
        fallback_model_ids=list(dict.fromkeys(payload.fallback_model_ids)),
        required_capabilities=list(dict.fromkeys(payload.required_capabilities)),
        is_active=payload.is_active,
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


def update_profile(db: Session, profile: ModelProfile, payload: ModelProfileUpdate) -> ModelProfile:
    updates = payload.model_dump(exclude_unset=True)
    if "primary_model_id" in updates or "fallback_model_ids" in updates:
        primary = updates.get("primary_model_id", profile.primary_model_id)
        fallbacks = updates.get("fallback_model_ids", profile.fallback_model_ids) or []
        _validate_model_ids(db, primary, list(fallbacks))
    if "fallback_model_ids" in updates and updates["fallback_model_ids"] is not None:
        updates["fallback_model_ids"] = list(dict.fromkeys(updates["fallback_model_ids"]))
    if "required_capabilities" in updates and updates["required_capabilities"] is not None:
        updates["required_capabilities"] = list(dict.fromkeys(updates["required_capabilities"]))
    for field, value in updates.items():
        setattr(profile, field, value)
    db.commit()
    db.refresh(profile)
    return profile


def _missing(capabilities: list[str], required: list[str]) -> list[str]:
    return [cap for cap in required if cap not in capabilities]


@dataclass(slots=True)
class ResolvedRoute:
    model: Model
    provider: ModelProvider
    used_fallback: bool


def resolve_profile(db: Session, profile_name: str) -> ResolvedRoute:
    """Resolve a logical profile to a concrete, capable, active model.

    Raises :class:`ProfileNotFound` for an unknown/inactive profile and
    :class:`RoutingError` when no candidate satisfies the profile's required
    capabilities (FR-3.3 - never silently downgrade).
    """
    profile = get_profile_by_name(db, profile_name)
    if profile is None or not profile.is_active:
        raise ProfileNotFound(profile_name)

    required = [
        c.value if isinstance(c, ModelCapability) else c for c in profile.required_capabilities
    ]

    candidate_ids: list[tuple[int, bool]] = []
    if profile.primary_model_id is not None:
        candidate_ids.append((profile.primary_model_id, False))
    for model_id in profile.fallback_model_ids:
        candidate_ids.append((model_id, True))

    if not candidate_ids:
        raise RoutingError(profile_name, "no models are configured for this profile")

    reasons: list[str] = []
    for model_id, is_fallback in candidate_ids:
        model = get_model(db, model_id)
        if model is None:
            reasons.append(f"model {model_id} does not exist")
            continue
        if not model.is_active:
            reasons.append(f"model '{model.name}' is inactive")
            continue
        if not model.provider.is_active:
            reasons.append(f"provider '{model.provider.name}' is inactive")
            continue
        capabilities = []
        for capability in model.capabilities:
            if isinstance(capability, ModelCapability):
                capabilities.append(capability.value)
            else:
                capabilities.append(str(capability))
        missing = _missing(capabilities, required)
        if missing:
            reasons.append(f"model '{model.name}' lacks {', '.join(missing)}")
            continue
        return ResolvedRoute(model=model, provider=model.provider, used_fallback=is_fallback)

    raise RoutingError(profile_name, "; ".join(reasons))
