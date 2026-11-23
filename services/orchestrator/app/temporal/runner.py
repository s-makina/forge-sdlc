"""Temporal worker runner for the orchestrator.

Starts a background worker that polls the orchestrator's task queue and runs the
durable workflows (feature-development and execution-run). The worker binds the
real execution-manager client into the pipeline activities so ``start-run``
submissions are actually executed.

The worker runs in a daemon thread alongside the FastAPI app (started from the
lifespan), so a single orchestrator process serves both the submission API and
the durable workflow execution.
"""

from __future__ import annotations

import threading
from typing import Any

from app.core.config import Settings
from app.execution.client import ExecutionManagerClient
from app.temporal import execution_workflow
from app.temporal.worker import register_worker


class TemporalWorkerRuntime:
    """Runs the orchestrator Temporal worker in a background daemon thread."""

    def __init__(
        self,
        *,
        host: str,
        namespace: str,
        task_queue: str,
        execution_manager: ExecutionManagerClient,
    ) -> None:
        self._host = host
        self._namespace = namespace
        self._task_queue = task_queue
        self._execution_manager = execution_manager
        self._thread: threading.Thread | None = None
        self._ready = threading.Event()

    def start(self) -> None:
        """Start the worker thread (idempotent)."""
        if self._thread is not None and self._thread.is_alive():
            return
        self._thread = threading.Thread(
            target=self._run,
            name="forgesdlc-temporal-worker",
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        """Signal the worker to shut down and wait for it to exit."""
        self._ready.set()

    def _run(self) -> None:
        from temporalio.client import Client  # type: ignore[import-untyped]

        # Bind the real execution-manager client so pipeline activities can reach
        # the execution-manager over the internal network.
        execution_workflow.bind_execution_client(self._execution_manager)
        try:
            client: Any = Client.connect(self._host, namespace=self._namespace)
            worker = register_worker(client, task_queue=self._task_queue)
            self._ready.set()
            worker.run()  # blocks until the thread is asked to shut down
        finally:
            execution_workflow.bind_execution_client(None)


def start_worker(settings: Settings, execution_manager: ExecutionManagerClient) -> TemporalWorkerRuntime:
    """Create and start the worker runtime from settings and a client."""
    runtime = TemporalWorkerRuntime(
        host=settings.temporal_host,
        namespace=settings.temporal_namespace,
        task_queue=settings.temporal_task_queue,
        execution_manager=execution_manager,
    )
    runtime.start()
    return runtime
