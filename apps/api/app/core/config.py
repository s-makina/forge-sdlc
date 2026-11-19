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

    # OpenHands (Phase 3 placeholder)
    openhands_base_url: str = ""


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()
