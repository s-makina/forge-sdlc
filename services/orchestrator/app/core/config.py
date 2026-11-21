"""Application configuration for the orchestrator worker."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Orchestrator worker settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "ForgeSDLC Orchestrator"
    environment: str = "development"
    debug: bool = True
    api_v1_prefix: str = "/api/v1"
    log_level: str = "INFO"

    # Control-plane API the orchestrator submits work against.
    control_plane_url: str = "http://localhost:8000"

    # Execution-manager API (Phase 4.4/4.6).
    execution_manager_url: str = "http://localhost:8001"

    # Temporal connection (Phase 4.1).
    temporal_host: str = "localhost:7233"
    temporal_namespace: str = "default"
    temporal_task_queue: str = "forgesdlc-workflows"

    # Workflow policy (mirrors apps/api workflow_timeout_seconds).
    workflow_timeout_seconds: int = 3600
    workflow_max_retries: int = 3


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()
