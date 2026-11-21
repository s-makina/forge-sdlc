"""Shared pytest fixtures for the orchestrator worker."""

import pytest
from fastapi.testclient import TestClient

from app.core.container import get_container
from app.main import create_app
from app.services.orchestrator import Orchestrator
from app.temporal.client import MemoryTemporalClient


@pytest.fixture()
def temporal_client() -> MemoryTemporalClient:
    """A fresh in-memory Temporal fake per test."""
    return MemoryTemporalClient()


@pytest.fixture()
def orchestrator(temporal_client: MemoryTemporalClient) -> Orchestrator:
    return Orchestrator(
        temporal_client,
        task_queue="forgesdlc-workflows",
        timeout_seconds=3600,
    )


@pytest.fixture()
def client(temporal_client: MemoryTemporalClient):
    """TestClient with the container wired to the in-memory Temporal fake."""
    container = get_container()
    container.register("temporal_client", temporal_client)
    container.register(
        "orchestrator",
        Orchestrator(
            temporal_client,
            task_queue="forgesdlc-workflows",
            timeout_seconds=3600,
        ),
    )
    app = create_app()
    yield TestClient(app)