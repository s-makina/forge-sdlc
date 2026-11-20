from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models.capabilities import ModelCapability
from app.models.model_provider import ModelProfile, ModelProvider, ProviderType


def default_profiles() -> list[tuple[str, str, list[str]]]:
    chat = ModelCapability.CHAT.value
    tool = ModelCapability.TOOL_CALLING.value
    structured = ModelCapability.STRUCTURED_OUTPUT.value
    streaming = ModelCapability.STREAMING.value
    vision = ModelCapability.VISION.value
    return [
        ("general-fast", "Classification and simple tasks", [chat, structured, streaming]),
        ("reasoning-strong", "Requirements, planning and architecture", [chat, structured]),
        ("coding-strong", "Complex implementation and debugging", [chat, tool, structured]),
        ("coding-fast", "Routine implementation", [chat, tool, streaming]),
        ("review-specialist", "Independent code review", [chat, structured]),
        ("documentation", "Technical documentation", [chat, streaming]),
        ("vision", "Screenshot and visual analysis", [chat, vision]),
    ]


def seed_default_providers(db: Session, settings: Settings) -> None:
    provider_count = int(db.scalar(select(func.count()).select_from(ModelProvider)) or 0)
    if provider_count == 0:
        db.add(
            ModelProvider(
                name="ollama-local",
                provider_type=ProviderType.OLLAMA.value,
                base_url=settings.ollama_base_url,
                credential_ref=None,
                timeout_seconds=settings.provider_probe_timeout_seconds,
                is_active=True,
            )
        )
        external_url = settings.external_model_base_url.strip()
        if external_url:
            db.add(
                ModelProvider(
                    name="external-openai",
                    provider_type=ProviderType.OPENAI_COMPATIBLE.value,
                    base_url=external_url,
                    credential_ref=settings.external_model_credential_ref.strip() or None,
                    timeout_seconds=settings.provider_probe_timeout_seconds,
                    is_active=True,
                )
            )

    profile_count = int(db.scalar(select(func.count()).select_from(ModelProfile)) or 0)
    if profile_count == 0:
        for name, description, required in default_profiles():
            db.add(
                ModelProfile(
                    name=name,
                    description=description,
                    required_capabilities=required,
                    fallback_model_ids=[],
                    is_active=True,
                )
            )

    db.commit()
