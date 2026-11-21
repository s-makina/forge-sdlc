"""Orchestrator service (Phase 4.1).

Coordinates durable workflows: submitting them to Temporal, signalling
cancellation, and reading back their durable status. The workflow *definition*
lives in the control-plane API (``apps/api``) and is mirrored here as the
workflow the orchestrator runs; agent conversations are never the record of
progress (README §10.3, FR-6.2). The orchestrator also hands scheduled work off
to the execution-manager (Phase 4.4/4.6).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.execution.client import ExecutionManagerClient, ExecutionRequest
from app.temporal.client import FEATURE_DEVELOPMENT_WORKFLOW_NAME, TemporalClient, WorkflowRun


@dataclass(frozen=True)
class WorkflowSubmission:
    """A workflow instance to run durably."""

    workflow_id: int
    project_id: int
    template_slug: str
    inputs: dict[str, Any]

    @property
    def durable_id(self) -> str:
        return f"workflow-{self.workflow_id}"


class WorkflowNotStarted(RuntimeError):
    pass


class Orchestrator:
    """Submits and manages workflow runs against a Temporal client."""

    def __init__(
        self,
        client: TemporalClient,
        *,
        task_queue: str,
        timeout_seconds: int,
        execution_manager: ExecutionManagerClient,
    ) -> None:
        self._client = client
        self._task_queue = task_queue
        self._timeout_seconds = timeout_seconds
        self._execution_manager = execution_manager

    @property
    def client(self) -> TemporalClient:
        return self._client

    @property
    def execution_manager(self) -> ExecutionManagerClient:
        return self._execution_manager

    def start(self, submission: WorkflowSubmission) -> WorkflowRun:
        """Submit a workflow instance to Temporal as a durable run."""
        return self._client.start_workflow(
            name=FEATURE_DEVELOPMENT_WORKFLOW_NAME,
            workflow_id=submission.durable_id,
            task_queue=self._task_queue,
            args=[submission],
            timeout_seconds=self._timeout_seconds,
        )

    def cancel(self, workflow_id: int) -> None:
        """Request cancellation of a running workflow instance."""
        self._client.cancel_workflow(f"workflow-{workflow_id}")

    def status(self, workflow_id: int) -> str:
        """Return the durable status of a workflow instance ('' if unknown)."""
        return self._client.workflow_status(f"workflow-{workflow_id}")

    def healthy(self) -> bool:
        return self._client.health()

    def request_execution(self, request: ExecutionRequest) -> str:
        """Request an execution from the execution-manager for a scheduled task.

        Returns the execution-manager's opaque execution id.
        """
        handle = self._execution_manager.request_execution(request)
        return handle.execution_id

    def execution_status(self, execution_id: str) -> str:
        """Return the execution-manager status for ``execution_id`` ('' if unknown)."""
        return self._execution_manager.execution_status(execution_id)
