"""FastAPI application entrypoint."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.container import get_container
from app.core.errors import register_error_handlers
from app.db.session import SessionLocal
from app.routers import (
    agents,
    approvals,
    audit,
    auth,
    executions,
    health,
    models,
    projects,
    registry,
    tasks,
    workflows,
)
from app.services.auth import bootstrap_operator
from app.services.seeds import seed_all


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    with SessionLocal() as db:
        bootstrap_operator(db)
        seed_all(db, get_settings())
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    # Initialise the DI container so process-wide singletons wire up at startup.
    get_container()

    application = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        lifespan=lifespan,
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",
            "http://dashboard:3000",
            "http://localhost",
            "http://localhost:80",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_error_handlers(application)

    application.include_router(health.router)
    prefix = settings.api_v1_prefix
    application.include_router(auth.router, prefix=prefix)
    application.include_router(projects.router, prefix=prefix)
    application.include_router(audit.router, prefix=prefix)
    application.include_router(agents.router, prefix=prefix)
    application.include_router(models.router, prefix=prefix)
    application.include_router(registry.router, prefix=prefix)
    application.include_router(tasks.router, prefix=prefix)
    application.include_router(executions.router, prefix=prefix)
    application.include_router(workflows.router, prefix=prefix)
    application.include_router(approvals.router, prefix=prefix)

    return application


app = create_app()
