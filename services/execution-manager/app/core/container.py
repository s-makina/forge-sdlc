"""Dependency-injection container for the execution-manager worker."""

from __future__ import annotations

from functools import lru_cache
from typing import cast

from app.core.config import Settings, get_settings
from app.docker.client import DockerClient, DockerSdkClient
from app.openhands.client import CodingRuntime, OpenHandsSdkRuntime


class Container:
    """Holds process-wide singletons (settings, docker client)."""

    def __init__(self) -> None:
        self._singletons: dict[str, object] = {
            "settings": get_settings(),
            "docker_client": DockerSdkClient(),
            "coding_runtime": OpenHandsSdkRuntime(base_url=get_settings().openhands_base_url),
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


@lru_cache
def get_container() -> Container:
    """Return the process-wide container."""
    return Container()