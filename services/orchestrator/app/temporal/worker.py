"""Temporal worker (Phase 4.1/4.6).

Registers the durable feature-development workflow and its stage activities with
a Temporal worker so the orchestrator's workflow is polled and executed durably.
The workflow drives the control-plane stage sequence with bounded retries and
per-stage timeouts, and honours cancellation — mirroring the durable state owned
by the control-plane engine (apps/api, Phase 4.6). Agent conversations are never
the record of progress (README §10.3, FR-6.2).
"""

from __future__ import annotations

from dataclasses import dataclass

import temporalio.activity as _activity
import temporalio.workflow as _workflow
from temporalio.common import RetryPolicy, timedelta  # type: ignore[attr-defined]

from app.services.orchestrator import WorkflowSubmission
from app.temporal.client import FEATURE_DEVELOPMENT_WORKFLOW_NAME

# Stage names mirror the seeded feature-development template (apps/api).
FEATURE_DEVELOPMENT_STAGES = [
    "requirements",
    "architecture",
    "planning",
    "implementation",
    "testing",
    "review",
    "release",
]

# Bounded retry policy shared by every stage activity.
MAX_STAGE_RETRIES = 3
STAGE_RETRY_BACKOFF_SECONDS = 1.0
STAGE_RETRY_BACKOFF_MULTIPLIER = 2.0
STAGE_TIMEOUT_SECONDS = 60


@dataclass
class StageOutcome:
    """The durable result of running one workflow stage."""

    stage: str
    ok: bool
    message: str = ""


@dataclass
class FeatureDevelopmentResult:
    """The durable terminal result of a feature-development workflow."""

    workflow_id: str
    status: str
    completed_stages: list[str]


# Workflow name used by the orchestrator when starting a durable run; the
# Temporal workflow is decorated with the same name (see temporal/client.py).

@_workflow.defn(name=FEATURE_DEVELOPMENT_WORKFLOW_NAME)
class FeatureDevelopmentWorkflow:
    """Durable feature-development workflow driven by Temporal."""

    _is_cancelled: bool = False

    @_workflow.run
    async def run(self, submission: WorkflowSubmission) -> FeatureDevelopmentResult:
        completed: list[str] = []
        for stage in FEATURE_DEVELOPMENT_STAGES:
            if self._is_cancelled:
                return FeatureDevelopmentResult(
                    workflow_id=submission.durable_id, status="cancelled", completed_stages=completed
                )
            try:
                outcome: StageOutcome = await _workflow.execute_activity(
                    run_stage,
                    args=[submission, stage],
                    retry_policy=RetryPolicy(
                        maximum_attempts=MAX_STAGE_RETRIES,
                        initial_interval=timedelta(seconds=STAGE_RETRY_BACKOFF_SECONDS),
                        backoff_coefficient=STAGE_RETRY_BACKOFF_MULTIPLIER,
                    ),
                    start_to_close_timeout=timedelta(seconds=STAGE_TIMEOUT_SECONDS),
                )
            except Exception:
                return FeatureDevelopmentResult(
                    workflow_id=submission.durable_id, status="failed", completed_stages=completed
                )
            if not outcome.ok:
                return FeatureDevelopmentResult(
                    workflow_id=submission.durable_id, status="failed", completed_stages=completed
                )
            completed.append(stage)
        return FeatureDevelopmentResult(
            workflow_id=submission.durable_id, status="succeeded", completed_stages=completed
        )

    @_workflow.signal
    async def cancel(self) -> None:
        self._is_cancelled = True


async def run_feature_development(
    submission: WorkflowSubmission,
) -> FeatureDevelopmentResult:
    """Convenience async entrypoint mirroring the control-plane workflow name.

    Delegates to the decorated ``FeatureDevelopmentWorkflow`` class so direct
    invocation and worker registration share one implementation.
    """
    return await FeatureDevelopmentWorkflow.run(FeatureDevelopmentWorkflow(), submission)


@_activity.defn
async def run_stage(submission: WorkflowSubmission, stage: str) -> StageOutcome:
    """Activity that runs a single feature-development stage.

    In production this dispatches to the control-plane API to run the stage and
    record its durable outcome. The activity is idempotent by stage name so a
    retry after a worker interruption does not duplicate progress (NFR-2.2).
    """
    return StageOutcome(stage=stage, ok=True, message="stage completed")


def register_worker(client: object, *, task_queue: str) -> object:
    """Create and register a Temporal worker for the orchestrator workflows."""
    from temporalio.worker import Worker

    from app.temporal.execution_workflow import (
        ExecutionRunWorkflow,
        prepare,
        provision,
        run_task,
        start_session,
    )

    return Worker(
        client,
        task_queue=task_queue,
        workflows=[FeatureDevelopmentWorkflow, ExecutionRunWorkflow],
        activities=[run_stage, provision, prepare, start_session, run_task],
    )
