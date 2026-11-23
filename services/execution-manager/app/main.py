"""FastAPI application entrypoint for the execution-manager worker."""

from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI

from app.core.config import get_settings
from app.db.session import Base, engine
from app.models import Execution, ExecutionArtefact, ExecutionEvent  # noqa: F401  (register models)
from app.routers import executions, health


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Ensure the execution-manager schema exists before serving requests.

    The execution-manager owns a small, self-contained set of tables
    (``executions``, ``execution_events``, ``execution_artefacts``) that live in
    the shared Postgres instance. Unlike the control-plane API it does not use
    Alembic; create tables idempotently on startup so a freshly-provisioned
    database works out of the box.
    """
    Base.metadata.create_all(bind=engine)
    yield


def create_app() -> FastAPI:
    settings = get_settings()

    application = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        lifespan=lifespan,
    )

    application.include_router(health.router)
    application.include_router(executions.router, prefix=settings.api_v1_prefix)

    return application


app = create_app()