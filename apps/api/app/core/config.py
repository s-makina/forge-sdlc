"""Application configuration via pydantic-settings."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "ForgeSDLC API"
    environment: str = "development"
    debug: bool = True
    api_v1_prefix: str = "/api/v1"
    log_level: str = "INFO"

    # Database
    database_url: str = "postgresql+psycopg://forgesdlc:forgesdlc@localhost:5432/forgesdlc"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Security
    session_secret_key: str = "change-me-in-production"
    session_cookie_name: str = "forgesdlc_session"
    session_max_age_seconds: int = 86400

    # Bootstrap operator
    bootstrap_operator_email: str = "operator@forgesdlc.local"
    bootstrap_operator_password: str = "change-me"

    # Model gateway (LiteLLM)
    litellm_base_url: str = "http://litellm:4000"
    litellm_master_key: str = ""
    litellm_config_path: str = ""
    provider_probe_timeout_seconds: int = 10

    # Default local Ollama endpoint seeded as a provider when empty
    ollama_base_url: str = "http://ollama:11434"

    # Optional external OpenAI-compatible provider seeded alongside Ollama.
    # Default points at NVIDIA NIM's OpenAI-compatible endpoint.
    external_model_base_url: str = "https://integrate.api.nvidia.com/v1"
    external_model_credential_ref: str = "env:EXTERNAL_MODEL_API_KEY"

    # OpenHands (Phase 3 placeholder)
    openhands_base_url: str = ""

    # Workflow orchestration (Phase 4)
    workflow_timeout_seconds: int = 3600
    workflow_max_retries: int = 3


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()
