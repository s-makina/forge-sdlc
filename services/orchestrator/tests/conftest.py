"""Shared pytest fixtures for the orchestrator worker."""

import pytest
from fastapi.testclient import TestClient

from app.core.container import get_container
from app.execution.client import MemoryExecutionManagerClient
from app.main import create_app
from app.services.orchestrator import Orchestrator
from app.temporal.client import MemoryTemporalClient


@pytest.fixture()
def temporal_client() -> MemoryTemporalClient:
    """A fresh in-memory Temporal fake per test."""
    return MemoryTemporalClient()


@pytest.fixture()
def execution_manager_client() -> MemoryExecutionManagerClient:
    """A fresh in-memory execution-manager fake per test."""
    return MemoryExecutionManagerClient()


@pytest.fixture()
def orchestrator(
    temporal_client: MemoryTemporalClient,
    execution_manager_client: MemoryExecutionManagerClient,
) -> Orchestrator:
    return Orchestrator(
        temporal_client,
        task_queue="forgesdlc-workflows",
        timeout_seconds=3600,
        execution_manager=execution_manager_client,
    )


@pytest.fixture()
def client(
    temporal_client: MemoryTemporalClient,
    execution_manager_client: MemoryExecutionManagerClient,
):
    """TestClient with the container wired to the in-memory fakes."""
    container = get_container()
    container.register("temporal_client", temporal_client)
    container.register("execution_manager_client", execution_manager_client)
    container.register(
        "orchestrator",
        Orchestrator(
            temporal_client,
            task_queue="forgesdlc-workflows",
            timeout_seconds=3600,
            execution_manager=execution_manager_client,
        ),
    )
    app = create_app()
    yield TestClient(app)
