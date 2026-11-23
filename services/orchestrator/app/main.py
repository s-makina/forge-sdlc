"""FastAPI application entrypoint for the orchestrator worker."""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.config import get_settings
from app.core.container import get_container
from app.routers import executions, health, workflows


@asynccontextmanager
async def lifespan(application: FastAPI):
    """Start the background Temporal worker when enabled, then serve."""
    settings = get_settings()
    if settings.start_worker:
        from app.temporal.runner import start_worker

        container = get_container()
        runtime = start_worker(settings, container.execution_manager_client)
        application.state.temporal_worker = runtime
        yield
        runtime.stop()
    else:
        yield


def create_app() -> FastAPI:
    settings = get_settings()

    application = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        lifespan=lifespan,
    )

    application.include_router(health.router)
    application.include_router(workflows.router, prefix=settings.api_v1_prefix)
    application.include_router(executions.router, prefix=settings.api_v1_prefix)

    return application


app = create_app()
