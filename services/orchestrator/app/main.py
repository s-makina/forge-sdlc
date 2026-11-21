"""FastAPI application entrypoint for the orchestrator worker."""

from fastapi import FastAPI

from app.core.config import get_settings
from app.routers import health, workflows


def create_app() -> FastAPI:
    settings = get_settings()

    application = FastAPI(
        title=settings.app_name,
        version="0.1.0",
    )

    application.include_router(health.router)
    application.include_router(workflows.router, prefix=settings.api_v1_prefix)

    return application


app = create_app()