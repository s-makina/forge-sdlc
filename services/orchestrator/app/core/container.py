"""Dependency-injection container for the orchestrator worker."""

from __future__ import annotations

from functools import lru_cache
from typing import cast

from app.core.config import Settings, get_settings
from app.execution.client import ExecutionManagerClient, HttpxExecutionManagerClient
from app.services.orchestrator import Orchestrator
from app.temporal.client import SdkTemporalClient, TemporalClient


class Container:
    """Holds process-wide singletons (settings, temporal client, orchestrator)."""

    def __init__(self) -> None:
        settings = get_settings()
        temporal_client: TemporalClient = SdkTemporalClient(
            host=settings.temporal_host,
            namespace=settings.temporal_namespace,
            task_queue=settings.temporal_task_queue,
        )
        execution_manager_client: ExecutionManagerClient = HttpxExecutionManagerClient(
            base_url=settings.execution_manager_url,
        )
        orchestrator = Orchestrator(
            temporal_client,
            task_queue=settings.temporal_task_queue,
            timeout_seconds=settings.workflow_timeout_seconds,
            execution_manager=execution_manager_client,
        )
        self._singletons: dict[str, object] = {
            "settings": settings,
            "temporal_client": temporal_client,
            "execution_manager_client": execution_manager_client,
            "orchestrator": orchestrator,
        }

    def register(self, name: str, instance: object) -> None:
        self._singletons[name] = instance

    def resolve(self, name: str) -> object:
        if name not in self._singletons:
            raise KeyError(f"No service registered under '{name}'")
        return self._singletons[name]

    @property
    def settings(self) -> Settings:
        return cast(Settings, self.resolve("settings"))

    @property
    def orchestrator(self) -> Orchestrator:
        return cast(Orchestrator, self.resolve("orchestrator"))

    @property
    def temporal_client(self) -> TemporalClient:
        return cast(TemporalClient, self.resolve("temporal_client"))

    @property
    def execution_manager_client(self) -> ExecutionManagerClient:
        return cast(ExecutionManagerClient, self.resolve("execution_manager_client"))


@lru_cache
def get_container() -> Container:
    """Return the process-wide container."""
    return Container()
