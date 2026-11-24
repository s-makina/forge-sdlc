"""Temporal client wrapper.

Abstracts the Temporal SDK behind a thin, injectable client so the orchestrator
logic (submitting workflow runs, signalling cancellation, querying status) is
testable without a live Temporal server (Phase 4.1).

The production implementation lazily resolves the ``temporalio`` SDK so the
rest of the package imports cleanly even when Temporal is unreachable at import
time.
"""

from __future__ import annotations

import abc
import asyncio
import threading
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

# Workflow name used when starting a durable run; matches the decorated Temporal
# workflow in ``app.temporal.worker``.
FEATURE_DEVELOPMENT_WORKFLOW_NAME = "forgesdlc_feature_development"

# Durable execution-run workflow name (drives the coding pipeline; see
# ``app.temporal.execution_workflow``).
EXECUTION_WORKFLOW_NAME = "forgesdlc_execution_run"


@dataclass(frozen=True)
class WorkflowRun:
    """A submitted durable workflow run and its identity."""

    workflow_id: str
    run_id: str = ""
    status: str = "pending"


class TemporalClient(abc.ABC):
    """Minimal Temporal surface used by the orchestrator."""

    @abc.abstractmethod
    def start_workflow(
        self,
        *,
        name: str,
        workflow_id: str,
        task_queue: str,
        args: list[Any],
        timeout_seconds: int,
    ) -> WorkflowRun:
        """Start a workflow and return its handle."""

    @abc.abstractmethod
    def cancel_workflow(self, workflow_id: str) -> None:
        """Request cancellation of a running workflow."""

    @abc.abstractmethod
    def workflow_status(self, workflow_id: str) -> str:
        """Return the current durable status of a workflow ('' if unknown)."""

    @abc.abstractmethod
    def health(self) -> bool:
        """Return True when the Temporal server is reachable."""


class SdkTemporalClient(TemporalClient):
    """Production Temporal client backed by the ``temporalio`` SDK.

    Lazily resolves the SDK so import-time doesn't require Temporal.

    The temporalio SDK is async-native while this service layer is synchronous,
    so the SDK client and every operation run on a single dedicated event loop
    owned by the client (a lock serializes concurrent access to that loop).
    """

    def __init__(self, *, host: str, namespace: str, task_queue: str) -> None:
        self._host = host
        self._namespace = namespace
        self._task_queue = task_queue
        self._client: Any | None = None
        self._loop = asyncio.new_event_loop()
        self._lock = threading.Lock()

    def _run(self, coro: Any) -> Any:
        with self._lock:
            return self._loop.run_until_complete(coro)

    def _resolve(self) -> Any:
        if self._client is None:
            with self._lock:
                if self._client is None:
                    from temporalio.client import Client  # type: ignore[import-untyped]

                    self._client = self._loop.run_until_complete(
                        Client.connect(self._host, namespace=self._namespace)
                    )
        return self._client

    def start_workflow(
        self,
        *,
        name: str,
        workflow_id: str,
        task_queue: str,
        args: list[Any],
        timeout_seconds: int,
    ) -> WorkflowRun:
        client = self._resolve()
        handle = self._run(
            client.start_workflow(
                name,
                *args,
                id=workflow_id,
                task_queue=task_queue,
                execution_timeout=timedelta(seconds=timeout_seconds),
            )
        )
        return WorkflowRun(workflow_id=workflow_id, run_id=handle.result_run_id)

    def cancel_workflow(self, workflow_id: str) -> None:
        self._run(self._resolve().get_workflow_handle(workflow_id).cancel())

    def workflow_status(self, workflow_id: str) -> str:
        """Return the durable status of a workflow ('' if it is unknown).

        Uses ``describe`` rather than ``result`` so a status query never blocks
        on the workflow completing (which could take up to the execution
        timeout).
        """
        client = self._resolve()
        try:
            handle = client.get_workflow_handle(workflow_id)
            description = self._run(handle.describe())
        except Exception:  # noqa: BLE001 - unknown/not-yet-started workflow
            return ""
        return description.status.name.lower()

    def health(self) -> bool:
        try:
            self._resolve().service  # noqa: B018 - connectivity probe
            return True
        except Exception:  # noqa: BLE001 - any failure means unreachable
            return False


class MemoryTemporalClient(TemporalClient):
    """In-memory fake Temporal client for tests and local development."""

    def __init__(self) -> None:
        self._runs: dict[str, WorkflowRun] = {}
        self._cancelled: set[str] = set()
        self._healthy = True

    def start_workflow(
        self,
        *,
        name: str,
        workflow_id: str,
        task_queue: str,
        args: list[Any],
        timeout_seconds: int,
    ) -> WorkflowRun:
        run = WorkflowRun(
            workflow_id=workflow_id,
            run_id=f"run-{workflow_id}",
            status="running",
        )
        self._runs[workflow_id] = run
        return run

    def cancel_workflow(self, workflow_id: str) -> None:
        self._cancelled.add(workflow_id)
        if workflow_id in self._runs:
            self._runs[workflow_id] = WorkflowRun(
                workflow_id=workflow_id,
                run_id=self._runs[workflow_id].run_id,
                status="cancelled",
            )

    def workflow_status(self, workflow_id: str) -> str:
        run = self._runs.get(workflow_id)
        return run.status if run else ""

    def health(self) -> bool:
        return self._healthy

    def set_healthy(self, healthy: bool) -> None:
        self._healthy = healthy
