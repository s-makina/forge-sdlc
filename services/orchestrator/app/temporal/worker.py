"""Temporal worker scaffold (Phase 4.1).

Registers the durable workflow functions with a Temporal worker so the
orchestrator's stage-running workflow can be polled and executed. The concrete
workflow body mirrors the control-plane engine (apps/api) which owns retries,
timeouts, cancellation and recovery (Phase 4.6).
"""

from __future__ import annotations

from app.services.orchestrator import WorkflowSubmission


def run_feature_development(submission: WorkflowSubmission) -> str:
    """Durable workflow entrypoint.

    In production this drives the workflow's stage runs against the control
    plane with retries/timeouts. For the Phase 4.1 scaffold it returns the
    durable workflow id; the control-plane engine (Phase 4.6) owns the durable
    stage logic.
    """
    return submission.durable_id


def register_worker(client: object, *, task_queue: str) -> object:
    """Create and register a Temporal worker for the orchestrator workflows.

    Lazily imports the ``temporalio`` worker so the module imports cleanly
    without the SDK installed.
    """
    from temporalio.worker import Worker  # type: ignore[import-untyped]

    return Worker(
        client,
        task_queue=task_queue,
        workflows=[run_feature_development],
    )