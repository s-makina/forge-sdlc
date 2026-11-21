"""Orchestrator service (Phase 4.1).

Coordinates durable workflows: submitting them to Temporal, signalling
cancellation, and reading back their durable status. The workflow *definition*
lives in the control-plane API (``apps/api``) and is mirrored here as the
workflow the orchestrator runs; agent conversations are never the record of
progress (README §10.3, FR-6.2).
"""

from __future__ import annotations

from dataclasses import dataclass

from app.temporal.client import TemporalClient, WorkflowRun


@dataclass(frozen=True)
class WorkflowSubmission:
    """A workflow instance to run durably."""

    workflow_id: int
    project_id: int
    template_slug: str
    inputs: dict[str, object]

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
    ) -> None:
        self._client = client
        self._task_queue = task_queue
        self._timeout_seconds = timeout_seconds

    @property
    def client(self) -> TemporalClient:
        return self._client

    def start(self, submission: WorkflowSubmission) -> WorkflowRun:
        """Submit a workflow instance to Temporal as a durable run."""
        return self._client.start_workflow(
            name="forgesdlc_feature_development",
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