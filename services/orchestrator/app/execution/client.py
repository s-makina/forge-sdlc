"""Execution-manager client wrapper.

Abstrahiert the execution-manager HTTP API behind a thin, injectable client so
the orchestrator logic (requesting an execution for a scheduled task, polling
its status, cancelling it) is testable without a live execution-manager service
(Phase 4.4/4.6).

The production implementation lazily resolves ``httpx`` so the rest of the
package imports cleanly even when the execution-manager is unreachable at import
time.
"""

from __future__ import annotations

import abc
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ExecutionRequest:
    """Payload describing an execution to request from the execution-manager."""

    project_id: int
    task_id: str | None = None
    repository_url: str | None = None
    branch: str = "main"
    image: str | None = None
    cpu_limit: float | None = None
    memory_limit: str | None = None
    disk_limit: str | None = None
    timeout_seconds: int | None = None
    network_policy: str | None = None


@dataclass(frozen=True)
class ExecutionHandle:
    """A requested execution and its observable state."""

    execution_id: str
    status: str = "created"


class ExecutionManagerClient(abc.ABC):
    """Minimal execution-manager surface used by the orchestrator."""

    @abc.abstractmethod
    def request_execution(self, request: ExecutionRequest) -> ExecutionHandle:
        """Request an execution and return its handle."""

    @abc.abstractmethod
    def execution_status(self, execution_id: str) -> str:
        """Return the current execution status ('' if unknown)."""

    @abc.abstractmethod
    def cancel_execution(self, execution_id: str) -> None:
        """Request cancellation of a running execution."""

    @abc.abstractmethod
    def health(self) -> bool:
        """Return True when the execution-manager is reachable."""


class HttpxExecutionManagerClient(ExecutionManagerClient):
    """Production execution-manager client backed by ``httpx``."""

    def __init__(self, *, base_url: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._http: Any | None = None

    def _resolve(self) -> Any:
        if self._http is None:
            import httpx

            self._http = httpx.Client(base_url=f"{self._base_url}/api/v1", timeout=30.0)
        return self._http

    def request_execution(self, request: ExecutionRequest) -> ExecutionHandle:
        http = self._resolve()
        response = http.post(
            "/executions",
            json={
                "project_id": request.project_id,
                "task_id": request.task_id,
                "repository_url": request.repository_url,
                "branch": request.branch,
                "image": request.image,
                "cpu_limit": request.cpu_limit,
                "memory_limit": request.memory_limit,
                "disk_limit": request.disk_limit,
                "timeout_seconds": request.timeout_seconds,
                "network_policy": request.network_policy,
            },
        )
        response.raise_for_status()
        data = response.json()
        return ExecutionHandle(
            execution_id=str(data["execution_id"]),
            status=str(data.get("status", "created")),
        )

    def execution_status(self, execution_id: str) -> str:
        http = self._resolve()
        try:
            response = http.get(f"/executions/{execution_id}/status")
        except Exception:  # noqa: BLE001 - unknown/unreachable execution
            return ""
        if response.status_code != 200:
            return ""
        return str(response.json().get("status", ""))

    def cancel_execution(self, execution_id: str) -> None:
        http = self._resolve()
        http.post(f"/executions/{execution_id}/cancel").raise_for_status()

    def health(self) -> bool:
        try:
            response = self._resolve().get("/health")
            return bool(response.status_code == 200)
        except Exception:  # noqa: BLE001 - any failure means unreachable
            return False


class MemoryExecutionManagerClient(ExecutionManagerClient):
    """In-memory fake execution-manager client for tests and local development."""

    def __init__(self) -> None:
        self._executions: dict[str, ExecutionHandle] = {}
        self._cancelled: set[str] = set()
        self._healthy = True
        self._counter = 0

    def request_execution(self, request: ExecutionRequest) -> ExecutionHandle:
        self._counter += 1
        execution_id = f"exec-{self._counter}"
        handle = ExecutionHandle(execution_id=execution_id, status="created")
        self._executions[execution_id] = handle
        return handle

    def execution_status(self, execution_id: str) -> str:
        handle = self._executions.get(execution_id)
        return handle.status if handle else ""

    def cancel_execution(self, execution_id: str) -> None:
        self._cancelled.add(execution_id)
        if execution_id in self._executions:
            self._executions[execution_id] = ExecutionHandle(
                execution_id=execution_id, status="cancelled"
            )

    def health(self) -> bool:
        return self._healthy

    def set_healthy(self, healthy: bool) -> None:
        self._healthy = healthy
