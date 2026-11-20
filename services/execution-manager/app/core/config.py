"""Application configuration via pydantic-settings."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Execution manager settings."""
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "ForgeSDLC Execution Manager"
    environment: str = "development"
    debug: bool = True
    api_v1_prefix: str = "/api/v1"
    log_level: str = "INFO"

    # Database
    database_url: str = "postgresql+psycopg://forgesdlc:forgesdlc@localhost:5432/forgesdlc"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Execution lifecycle defaults (README §12.2)
    workspace_image: str = "python:3.12-slim"
    workspace_cpu_limit: float = 1.0
    workspace_memory_limit: str = "1g"
    workspace_disk_limit: str = "2g"
    workspace_timeout_seconds: int = 3600
    workspace_network_policy: str = "minimal"
    workspace_network_allowlist: str = ""  # comma-separated host allowlist
    cleanup_retention_seconds: int = 3600

    # Artifact storage (S3-compatible object storage; empty disables storage)
    artifact_bucket: str = ""
    artifact_endpoint_url: str = ""
    artifact_access_key: str = ""
    artifact_secret_key: str = ""

    # OpenHands runtime (Phase 3.4 placeholder)
    openhands_base_url: str = ""


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()