"""Dependency-injection helpers for the execution-manager."""

from __future__ import annotations

from fastapi import Depends

from app.core.container import Container, get_container
from app.docker.client import DockerClient
from app.openhands.client import CodingRuntime


def get_container_dep() -> Container:
    """Return the process-wide DI container."""
    return get_container()


def get_docker_client(
    container: Container = Depends(get_container_dep),
) -> DockerClient:
    """Return the Docker client singleton (overridable in tests)."""
    return container.docker_client


def get_coding_runtime(
    container: Container = Depends(get_container_dep),
) -> CodingRuntime:
    """Return the OpenHands coding runtime singleton (overridable in tests)."""
    return container.coding_runtime