"""Dependency-injection container for the execution-manager worker."""

from __future__ import annotations

from functools import lru_cache
from typing import cast

from app.core.config import Settings, get_settings
from app.docker.client import DockerClient, DockerSdkClient
from app.openhands.client import CodingRuntime, OpenHandsSdkRuntime
from app.storage.client import MemoryObjectStore, ObjectStore, S3ObjectStore


def _build_object_store(settings: Settings) -> ObjectStore:
    """Return the configured object store (S3 when a bucket is set, else memory)."""
    if settings.artifact_bucket:
        return S3ObjectStore(settings)
    return MemoryObjectStore()


class Container:
    """Holds process-wide singletons (settings, docker client, object store)."""

    def __init__(self) -> None:
        settings = get_settings()
        self._singletons: dict[str, object] = {
            "settings": settings,
            "docker_client": DockerSdkClient(),
            "coding_runtime": OpenHandsSdkRuntime(base_url=settings.openhands_base_url),
            "object_store": _build_object_store(settings),
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
    def docker_client(self) -> DockerClient:
        return cast(DockerClient, self.resolve("docker_client"))

    @property
    def coding_runtime(self) -> CodingRuntime:
        return cast(CodingRuntime, self.resolve("coding_runtime"))

    @property
    def object_store(self) -> ObjectStore:
        return cast(ObjectStore, self.resolve("object_store"))


@lru_cache
def get_container() -> Container:
    """Return the process-wide container."""
    return Container()