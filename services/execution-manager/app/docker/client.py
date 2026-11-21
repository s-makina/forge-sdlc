"""Docker client wrapper.

Abstracts the Docker Engine API behind a thin, injectable client so the
workspace-provisioning logic is testable without a live Docker daemon.

The production implementation talks to the local Docker daemon over the Unix
socket / named pipe via the ``docker`` SDK. The host socket is never mounted
into agent workspaces (README §12.3): the execution-manager controls the daemon
*outside* the workspace container.
"""

from __future__ import annotations

import abc
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ContainerSpec:
    """A workspace container to create."""

    name: str
    image: str
    working_dir: str
    cpu_limit: float
    memory_limit: str
    disk_limit: str
    network_policy: str
    network_allowlist: list[str]
    environment: dict[str, str]
    mounts: list[dict[str, str]] = field(default_factory=list)
    command: list[str] = field(default_factory=list)


class DockerClient(abc.ABC):
    """Minimal Docker Engine API surface used by the execution manager."""

    @abc.abstractmethod
    def create_container(self, spec: ContainerSpec) -> str:
        """Create a container and return its id."""

    @abc.abstractmethod
    def start_container(self, container_id: str) -> None:
        """Start a created container."""

    @abc.abstractmethod
    def stop_container(self, container_id: str) -> None:
        """Stop a running container."""

    @abc.abstractmethod
    def remove_container(self, container_id: str) -> None:
        """Remove a stopped container."""

    @abc.abstractmethod
    def container_status(self, container_id: str) -> str:
        """Return the container status (e.g. created/running/exited)."""

    @abc.abstractmethod
    def get_container_logs(self, container_id: str) -> str:
        """Return the container's captured output."""

    @abc.abstractmethod
    def exec_run(self, container_id: str, cmd: list[str]) -> tuple[int, str]:
        """Run a command inside a running container; return (exit_code, output)."""


class DockerSdkClient(DockerClient):
    """Production Docker client backed by the ``docker`` Python SDK.

    Lazily resolves the SDK so the rest of the package imports cleanly even when
    Docker is unavailable at import time.
    """

    def __init__(self) -> None:
        self._client: Any | None = None

    def _resolve(self) -> Any:
        if self._client is None:
            import docker  # type: ignore[import-untyped]

            self._client = docker.from_env()
        return self._client

    def create_container(self, spec: ContainerSpec) -> str:
        client = self._resolve()
        container = client.containers.create(
            image=spec.image,
            name=spec.name,
            working_dir=spec.working_dir,
            command=spec.command,
            environment=spec.environment,
            volumes=spec.mounts,
            network=spec.network_policy,
            mem_limit=spec.memory_limit,
            nano_cpus=int(spec.cpu_limit * 1_000_000_000),
            pids_limit=256,
            user="1000:1000",
            read_only=not spec.mounts,
        )
        return container.id

    def start_container(self, container_id: str) -> None:
        self._resolve().containers.get(container_id).start()

    def stop_container(self, container_id: str) -> None:
        self._resolve().containers.get(container_id).stop(timeout=10)

    def remove_container(self, container_id: str) -> None:
        self._resolve().containers.get(container_id).remove(force=True)

    def container_status(self, container_id: str) -> str:
        return self._resolve().containers.get(container_id).status

    def get_container_logs(self, container_id: str) -> str:
        logs = self._resolve().containers.get(container_id).logs()
        return logs.decode("utf-8", errors="replace") if isinstance(logs, bytes) else str(logs)

    def exec_run(self, container_id: str, cmd: list[str]) -> tuple[int, str]:
        result = self._resolve().containers.get(container_id).exec_run(cmd, demux=False)
        exit_code = result[0]
        output = result[1]
        decoded = output.decode("utf-8", errors="replace") if isinstance(output, bytes) else str(output)
        return exit_code, decoded