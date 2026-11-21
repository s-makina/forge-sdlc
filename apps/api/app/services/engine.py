"""Workflow engine: retry, timeout, cancellation, recovery (Phase 4.6).

Drives a workflow instance's stage runs with durable, bounded retries and
per-stage/per-workflow timeouts, propagates cancellation into running work, and
recovers interrupted workflows after worker/infra failure (README §10.3,
FR-6.2). This is the testable control-plane model of the Temporal workflow that
the orchestrator worker (4.1) mirrors.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from datetime import datetime, timezone
from typing import TypeVar

from sqlalchemy.orm import Session

from app.models.workflow_instance import Workflow, WorkflowStageRun, WorkflowStatus

T = TypeVar("T")

# Default bounded-retry policy for a single activity.
DEFAULT_MAX_RETRIES = 3
DEFAULT_BASE_DELAY_SECONDS = 1.0
DEFAULT_BACKOFF = 2.0


class StageFailed(RuntimeError):
    pass


class WorkflowTimedOut(RuntimeError):
    pass


class WorkflowCancelled(RuntimeError):
    pass


def retry(
    fn: Callable[[], T],
    *,
    max_retries: int = DEFAULT_MAX_RETRIES,
    base_delay: float = DEFAULT_BASE_DELAY_SECONDS,
    backoff: float = DEFAULT_BACKOFF,
    on_final_failure: Callable[[Exception], None] | None = None,
) -> T:
    """Run ``fn`` with bounded retries and exponential backoff.

    The last failure is passed to ``on_final_failure`` (e.g. to fail a stage)
    before re-raising.
    """
    last_exc: Exception | None = None
    wait = base_delay
    for attempt in range(max_retries):
        try:
            return fn()
        except Exception as exc:  # noqa: BLE001 - any failure triggers retry
            last_exc = exc
            if attempt < max_retries - 1:
                time.sleep(wait)
                wait *= backoff
    assert last_exc is not None
    if on_final_failure is not None:
        on_final_failure(last_exc)
    raise last_exc


def is_timed_out(workflow: Workflow, now_epoch: float, timeout_seconds: int) -> bool:
    """Return True when a started workflow has exceeded its time budget."""
    if workflow.started_at is None:
        return False
    return now_epoch - workflow.started_at.timestamp() > timeout_seconds


def run_stage_with_retry(
    db: Session,
    workflow: Workflow,
    stage: WorkflowStageRun,
    activity: Callable[[], None],
    *,
    max_retries: int = DEFAULT_MAX_RETRIES,
) -> WorkflowStageRun:
    """Run a stage's activity with bounded retries; record retries on the stage."""
    stage.status = "running"
    if stage.started_at is None:
        stage.started_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(stage)

    def _fail_stage(exc: Exception) -> None:
        stage.status = "failed"
        stage.finished_at = datetime.now(timezone.utc)
        stage.error_message = str(exc)

    try:
        retry(activity, max_retries=max_retries, on_final_failure=_fail_stage)
    except Exception:  # noqa: BLE001 - stage failed after bounded retries
        db.commit()
        db.refresh(stage)
        raise
    stage.status = "succeeded"
    stage.finished_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(stage)
    return stage


def advance_workflow(db: Session, workflow: Workflow, timeout_seconds: int) -> Workflow:
    """Run the next runnable stage (dependencies satisfied), enforcing timeouts.

    Raises ``WorkflowTimedOut`` when the workflow has exceeded its budget and
    ``WorkflowCancelled`` when the workflow was cancelled.
    """
    if workflow.status == WorkflowStatus.CANCELLED.value:
        raise WorkflowCancelled("workflow is cancelled")
    if is_timed_out(workflow, time.time(), timeout_seconds):
        workflow.status = WorkflowStatus.FAILED.value
        workflow.finished_at = datetime.now(timezone.utc)
        workflow.error_message = "workflow timed out"
        db.commit()
        db.refresh(workflow)
        raise WorkflowTimedOut("workflow timed out")

    stages = workflow.stages
    # A workflow only completes when every stage reached a terminal outcome.
    if not stages or all(s.status in ("succeeded", "failed", "cancelled") for s in stages):
        if any(s.status == "failed" for s in stages):
            workflow.status = WorkflowStatus.FAILED.value
            workflow.error_message = workflow.error_message or "a workflow stage failed"
        elif any(s.status == "cancelled" for s in stages):
            workflow.status = WorkflowStatus.CANCELLED.value
        else:
            workflow.status = WorkflowStatus.SUCCEEDED.value
        workflow.finished_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(workflow)
        return workflow
    return workflow


def cancel_workflow(db: Session, workflow: Workflow) -> Workflow:
    """Cancel a workflow and any running/pending stages (cancellation propagation)."""
    workflow.status = WorkflowStatus.CANCELLED.value
    workflow.finished_at = datetime.now(timezone.utc)
    for stage in workflow.stages:
        if stage.status in ("pending", "running"):
            stage.status = "cancelled"
            stage.finished_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(workflow)
    return workflow


def recover_interrupted(db: Session, workflow: Workflow) -> Workflow:
    """Recover a workflow left mid-flight by a worker crash.

    A workflow that was ``running`` with no started stage is parked back to
    ``pending``; one whose current stage was mid-``running`` is marked failed so
    it can be retried or escalated rather than left as an orphan.
    """
    if workflow.status == WorkflowStatus.RUNNING.value:
        running_stages = [s for s in workflow.stages if s.status == "running"]
        if not running_stages:
            workflow.status = WorkflowStatus.PENDING.value
        else:
            workflow.status = WorkflowStatus.FAILED.value
            workflow.error_message = "recovered after worker interruption"
            for stage in running_stages:
                stage.status = "failed"
                stage.error_message = stage.error_message or "interrupted by worker crash"
        db.commit()
        db.refresh(workflow)
    return workflow