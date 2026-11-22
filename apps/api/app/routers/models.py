"""Model gateway routes: providers, models, profiles, health reading, usage."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.secrets import CredentialError
from app.db.session import get_db
from app.deps.auth import require_operator, require_user
from app.models.capabilities import ModelCapability
from app.models.model_provider import Model, ModelProfile, ModelProvider, UsageRecord
from app.models.user import User
from app.schemas.models import (
    CapabilityItem,
    CapabilityResult,
    ConnectivityResult,
    GatewayConfigApplyResult,
    GatewayConfigRead,
    HealthSummary,
    ModelCapabilitiesRead,
    ModelCreate,
    ModelList,
    ModelProfileCreate,
    ModelProfileList,
    ModelProfileRead,
    ModelProfileUpdate,
    ModelProviderCreate,
    ModelProviderList,
    ModelProviderRead,
    ModelProviderUpdate,
    ModelRead,
    ModelUpdate,
    ProfileResolutionRead,
    ProviderCheckList,
    ProviderCheckRead,
    ProviderHealth,
    UsageCreate,
    UsageList,
    UsageRead,
    UsageSummary,
)
from app.services import audit, model_gateway, model_providers, provider_health

router = APIRouter(prefix="/models", tags=["models"])


@router.get("/capabilities", response_model=ModelCapabilitiesRead)
def list_capabilities(_: User = Depends(require_user)) -> ModelCapabilitiesRead:
    return ModelCapabilitiesRead(items=[CapabilityItem(value=c.value, description=c.name) for c in ModelCapability])


@router.get("/providers", response_model=ModelProviderList)
def list_providers(
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    _: User = Depends(require_user),
) -> ModelProviderList:
    items = model_providers.list_providers(db, include_inactive=include_inactive)
    return ModelProviderList(
        items=[ModelProviderRead.model_validate(p) for p in items], total=len(items)
    )


def _get_provider_or_404(db: Session, provider_id: int) -> ModelProvider:
    provider = model_providers.get_provider(db, provider_id)
    if provider is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Provider not found")
    return provider


def _get_model_or_404(db: Session, model_id: int) -> Model:
    model = model_providers.get_model(db, model_id)
    if model is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Model not found")
    return model


def _get_profile_or_404(db: Session, profile_id: int) -> ModelProfile:
    profile = model_providers.get_profile(db, profile_id)
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")
    return profile


@router.post("/providers", response_model=ModelProviderRead, status_code=status.HTTP_201_CREATED)
def create_provider(
    payload: ModelProviderCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_operator),
) -> ModelProviderRead:
    try:
        provider = model_providers.create_provider(db, payload)
    except model_providers.DuplicateName as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except CredentialError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    audit.record_audit(
        db,
        action="model_provider.create",
        entity_type="model_provider",
        entity_id=str(provider.id),
        actor_id=user.id,
        actor_email=user.email,
        details=f"Created provider '{provider.name}' ({provider.provider_type})",
    )
    return ModelProviderRead.model_validate(provider)


@router.get("/providers/{provider_id}", response_model=ModelProviderRead)
def get_provider(
    provider_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_user),
) -> ModelProviderRead:
    return ModelProviderRead.model_validate(_get_provider_or_404(db, provider_id))


@router.patch("/providers/{provider_id}", response_model=ModelProviderRead)
def update_provider(
    provider_id: int,
    payload: ModelProviderUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_operator),
) -> ModelProviderRead:
    provider = _get_provider_or_404(db, provider_id)
    try:
        updated = model_providers.update_provider(db, provider, payload)
    except model_providers.DuplicateName as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except CredentialError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    audit.record_audit(
        db,
        action="model_provider.update",
        entity_type="model_provider",
        entity_id=str(updated.id),
        actor_id=user.id,
        actor_email=user.email,
        details=f"Updated provider '{updated.name}'",
    )
    return ModelProviderRead.model_validate(updated)


def _provider_models(db: Session, provider_id: int) -> list[Model]:
    return list(db.scalars(select(Model).where(Model.provider_id == provider_id)).all())


@router.post(
    "/providers/{provider_id}/models",
    response_model=ModelRead,
    status_code=status.HTTP_201_CREATED,
)
def create_model(
    provider_id: int,
    payload: ModelCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
) -> ModelRead:
    provider = _get_provider_or_404(db, provider_id)
    try:
        model = model_providers.create_model(db, provider, payload)
    except model_providers.DuplicateName as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    audit.record_audit(
        db,
        action="model.create",
        entity_type="model",
        entity_id=str(model.id),
        actor_id=user.id,
        actor_email=user.email,
        details=f"Registered model '{model.name}' on provider '{provider.name}'",
    )
    read = ModelRead.model_validate(model)
    read.provider_name = provider.name
    return read


@router.get("/providers/{provider_id}/models", response_model=ModelList)
def list_provider_models(
    provider_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_user),
) -> ModelList:
    provider = _get_provider_or_404(db, provider_id)
    rows = _provider_models(db, provider_id)
    items = []
    for row in rows:
        read = ModelRead.model_validate(row)
        read.provider_name = provider.name
        items.append(read)
    return ModelList(items=items, total=len(items))


@router.get("/items", response_model=ModelList)
def list_models(
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    _: User = Depends(require_user),
) -> ModelList:
    rows = model_providers.list_models(db, include_inactive=include_inactive)
    items = []
    for row in rows:
        read = ModelRead.model_validate(row)
        read.provider_name = row.provider.name
        items.append(read)
    return ModelList(items=items, total=len(items))


@router.patch("/items/{model_id}", response_model=ModelRead)
def update_model(
    model_id: int,
    payload: ModelUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
) -> ModelRead:
    model = _get_model_or_404(db, model_id)
    updated = model_providers.update_model(db, model, payload)
    audit.record_audit(
        db,
        action="model.update",
        entity_type="model",
        entity_id=str(updated.id),
        actor_id=user.id,
        actor_email=user.email,
        details=f"Updated model '{updated.name}'",
    )
    read = ModelRead.model_validate(updated)
    read.provider_name = updated.provider.name
    return read


@router.get("/profiles", response_model=ModelProfileList)
def list_profiles(
    db: Session = Depends(get_db),
    _: User = Depends(require_user),
) -> ModelProfileList:
    rows = model_providers.list_profiles(db)
    return ModelProfileList(
        items=[ModelProfileRead.model_validate(p) for p in rows], total=len(rows)
    )


@router.post("/profiles", response_model=ModelProfileRead, status_code=status.HTTP_201_CREATED)
def create_profile(
    payload: ModelProfileCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
) -> ModelProfileRead:
    try:
        profile = model_providers.create_profile(db, payload)
    except model_providers.DuplicateName as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except model_providers.ProviderNotFound as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    audit.record_audit(
        db,
        action="model_profile.create",
        entity_type="model_profile",
        entity_id=str(profile.id),
        actor_id=user.id,
        actor_email=user.email,
        details=f"Created model profile '{profile.name}'",
    )
    return ModelProfileRead.model_validate(profile)


@router.patch("/profiles/{profile_id}", response_model=ModelProfileRead)
def update_profile(
    profile_id: int,
    payload: ModelProfileUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
) -> ModelProfileRead:
    profile = _get_profile_or_404(db, profile_id)
    try:
        updated = model_providers.update_profile(db, profile, payload)
    except model_providers.ProviderNotFound as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    audit.record_audit(
        db,
        action="model_profile.update",
        entity_type="model_profile",
        entity_id=str(updated.id),
        actor_id=user.id,
        actor_email=user.email,
        details=f"Updated model profile '{updated.name}'",
    )
    return ModelProfileRead.model_validate(updated)


@router.get("/profiles/{profile_name}/resolve", response_model=ProfileResolutionRead)
def resolve_profile(
    profile_name: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_user),
) -> ProfileResolutionRead:
    try:
        route = model_providers.resolve_profile(db, profile_name)
    except model_providers.ProfileNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except model_providers.RoutingError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    profile = model_providers.get_profile_by_name(db, profile_name)
    assert profile is not None
    return ProfileResolutionRead(
        profile=profile.name,
        required_capabilities=list(profile.required_capabilities),
        model=ModelRead.model_validate(route.model),
        provider=ModelProviderRead.model_validate(route.provider),
        used_fallback=route.used_fallback,
    )


def _store_check(
    db: Session,
    *,
    provider: ModelProvider,
    result: provider_health.ProbeResult,
    model_id: int | None = None,
) -> None:
    from app.models.model_provider import CheckKind, ProviderCheck

    db.add(
        ProviderCheck(
            provider_id=provider.id,
            model_id=model_id,
            kind=CheckKind.CONNECTIVITY.value if model_id is None else CheckKind.CAPABILITY.value,
            status=result.status,
            latency_ms=result.latency_ms,
            detail=result.detail,
        )
    )
    db.commit()


@router.get("/health", response_model=HealthSummary)
def provider_health_summary(
    db: Session = Depends(get_db),
    _: User = Depends(require_user),
) -> HealthSummary:
    client = provider_health.ProviderProbeClient()
    items: list[ProviderHealth] = []
    for provider in model_providers.list_providers(db):
        models = _provider_models(db, provider.id)
        result = client.connectivity(provider)
        caps = provider_health.probe_capabilities(models)
        checked_at = datetime.now(UTC)
        _store_check(db, provider=provider, result=result)
        items.append(
            ProviderHealth(
                provider_id=provider.id,
                provider_name=provider.name,
                provider_type=provider.provider_type,
                base_url=provider.base_url,
                status=result.status,
                connectivity=ConnectivityResult(
                    ok=result.status == provider_health.STATUS_OK,
                    latency_ms=result.latency_ms,
                    detail=result.detail,
                ),
                capabilities={
                    name: CapabilityResult(capability=name, supported=value, detail=None)
                    for name, value in caps.items()
                },
                checked_at=checked_at,
                model_count=len(models),
            )
        )
    return HealthSummary(items=items, total=len(items))


@router.post("/providers/{provider_id}/check", response_model=ProviderHealth)
def check_provider(
    provider_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
) -> ProviderHealth:
    provider = _get_provider_or_404(db, provider_id)
    models = _provider_models(db, provider.id)
    client = provider_health.ProviderProbeClient()
    result = client.connectivity(provider)
    caps = provider_health.probe_capabilities(models)
    _store_check(db, provider=provider, result=result)
    audit.record_audit(
        db,
        action="model_provider.check",
        entity_type="model_provider",
        entity_id=str(provider.id),
        actor_id=user.id,
        actor_email=user.email,
        details=f"Checked provider '{provider.name}' -> {result.status}",
    )
    return ProviderHealth(
        provider_id=provider.id,
        provider_name=provider.name,
        provider_type=provider.provider_type,
        base_url=provider.base_url,
        status=result.status,
        connectivity=ConnectivityResult(
            ok=result.status == provider_health.STATUS_OK,
            latency_ms=result.latency_ms,
            detail=result.detail,
        ),
        capabilities={
            name: CapabilityResult(capability=name, supported=value, detail=None)
            for name, value in caps.items()
        },
        checked_at=datetime.now(UTC),
        model_count=len(models),
    )


@router.get("/providers/{provider_id}/checks", response_model=ProviderCheckList)
def list_provider_checks(
    provider_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_user),
) -> ProviderCheckList:
    from app.models.model_provider import ProviderCheck

    _get_provider_or_404(db, provider_id)
    rows = list(
        db.scalars(
            select(ProviderCheck)
            .where(ProviderCheck.provider_id == provider_id)
            .order_by(ProviderCheck.id.desc())
            .limit(100)
        ).all()
    )
    return ProviderCheckList(
        items=[ProviderCheckRead.model_validate(r) for r in rows], total=len(rows)
    )


@router.post("/usage", response_model=UsageRead, status_code=status.HTTP_201_CREATED)
def record_usage(
    payload: UsageCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_user),
) -> UsageRead:
    if payload.provider_id is not None and db.get(ModelProvider, payload.provider_id) is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"provider {payload.provider_id} not found",
        )
    if payload.model_id is not None and db.get(Model, payload.model_id) is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"model {payload.model_id} not found",
        )
    if payload.agent_version_id is not None:
        from app.models.agent import AgentVersion

        if db.get(AgentVersion, payload.agent_version_id) is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"agent_version {payload.agent_version_id} not found",
            )
    record = UsageRecord(
        provider_id=payload.provider_id,
        model_id=payload.model_id,
        profile_name=payload.profile_name,
        agent_version_id=payload.agent_version_id,
        input_tokens=payload.input_tokens,
        output_tokens=payload.output_tokens,
        total_tokens=payload.total_tokens,
        cost_usd=payload.cost_usd,
        success=payload.success,
        latency_ms=payload.latency_ms,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return UsageRead.model_validate(record)


@router.get("/usage", response_model=UsageSummary)
def usage_summary(
    db: Session = Depends(get_db),
    _: User = Depends(require_user),
) -> UsageSummary:
    rows = list(db.scalars(select(UsageRecord).order_by(UsageRecord.id.desc()).limit(200)).all())
    total = int(db.scalar(select(func.count()).select_from(UsageRecord)) or 0)
    input_tokens = int(db.scalar(select(func.coalesce(func.sum(UsageRecord.input_tokens), 0))) or 0)
    output_tokens = int(
        db.scalar(select(func.coalesce(func.sum(UsageRecord.output_tokens), 0))) or 0
    )
    total_tokens = int(db.scalar(select(func.coalesce(func.sum(UsageRecord.total_tokens), 0))) or 0)
    cost = float(db.scalar(select(func.coalesce(func.sum(UsageRecord.cost_usd), 0))) or 0)
    return UsageSummary(
        total_calls=total,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=total_tokens,
        total_cost_usd=cost,
        items=[UsageRead.model_validate(r) for r in rows],
    )


@router.get("/usage/records", response_model=UsageList)
def list_usage(
    db: Session = Depends(get_db),
    _: User = Depends(require_user),
) -> UsageList:
    rows = list(db.scalars(select(UsageRecord).order_by(UsageRecord.id.desc()).limit(200)).all())
    total = int(db.scalar(select(func.count()).select_from(UsageRecord)) or 0)
    return UsageList(items=[UsageRead.model_validate(r) for r in rows], total=total)


@router.get("/gateway/config", response_model=GatewayConfigRead)
def gateway_config(
    db: Session = Depends(get_db),
    _: User = Depends(require_user),
) -> GatewayConfigRead:
    providers = model_providers.list_providers(db)
    config = model_gateway.render_litellm_config(providers)
    return GatewayConfigRead(
        generated_at=datetime.now(UTC),
        model_count=len(config.get("model_list", [])),
        config=config,
    )


@router.get("/gateway/config.yaml")
def gateway_config_yaml(
    db: Session = Depends(get_db),
    _: User = Depends(require_user),
) -> Response:
    providers = model_providers.list_providers(db)
    body = model_gateway.render_litellm_yaml(providers)
    return Response(content=body, media_type="application/yaml")


@router.post("/gateway/config/apply", response_model=GatewayConfigApplyResult)
def apply_gateway_config(
    db: Session = Depends(get_db),
    user: User = Depends(require_operator),
    settings: Settings = Depends(get_settings),
) -> GatewayConfigApplyResult:
    """Write the generated LiteLLM config to the configured path.

    LiteLLM reads its config at startup, so the running proxy must be
    reloaded or restarted before it serves the new model list.
    """
    path = settings.litellm_config_path.strip()
    if not path:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="LITELLM_CONFIG_PATH is not configured",
        )
    providers = model_providers.list_providers(db)
    try:
        count = model_gateway.write_litellm_config(providers, path)
    except CredentialError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except OSError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not write gateway config: {exc.strerror or exc}",
        ) from exc

    reloaded = model_gateway.reload_litellm(
        settings.litellm_base_url, settings.litellm_master_key
    )

    audit.record_audit(
        db,
        action="model_gateway.apply",
        entity_type="model_gateway",
        entity_id=path,
        actor_id=user.id,
        actor_email=user.email,
        details=f"Wrote {count} model(s) to gateway config; reloaded={reloaded}",
    )
    return GatewayConfigApplyResult(
        written=True,
        path=path,
        model_count=count,
        reloaded=reloaded,
        generated_at=datetime.now(UTC),
    )
