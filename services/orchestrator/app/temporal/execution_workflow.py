"""Durable execution-run workflow (Phase 4.4/4.6).

Drives the coding pipeline for a single task execution durably against
Temporal: create -> provision -> prepare (clone) -> start-session -> run. Each
step is a bounded activity that calls the execution-manager's existing
endpoints, so a worker interruption or activity retry resumes the pipeline at
the point it left off (the execution-manager owns the durable execution
lifecycle; agent conversations are never the record of progress, README
§10.3/FR-6.2).

The control-plane API creates the execution (recording its id on the task) and
submits this workflow with that id; the workflow then drives the remaining
steps and reports the terminal outcome.
"""

from __future__ import annotations

from dataclasses import dataclass

import temporalio.activity as _activity
import temporalio.workflow as _workflow
from temporalio.common import RetryPolicy, timedelta  # type: ignore[attr-defined]

from app.execution.client import ExecutionManagerClient, RunOutcome
from app.temporal.client import EXECUTION_WORKFLOW_NAME

# Bounded retry policy shared by every pipeline activity.
MAX_RUN_RETRIES = 3
RUN_RETRY_BACKOFF_SECONDS = 1.0
RUN_RETRY_BACKOFF_MULTIPLIER = 2.0
RUN_ACTIVITY_TIMEOUT_SECONDS = 900


@dataclass(frozen=True)
class ExecutionRunSubmission:
    """The durable inputs for driving one task execution through the pipeline."""

    execution_id: str
    task_id: str = ""
    project_id: int = 0
    prompt: str = ""


@dataclass
class ExecutionRunResult:
    """The durable terminal result of an execution-run workflow."""

    execution_id: str
    status: str
    message: str = ""


# ---------------------------------------------------------------------------
# Activity-to-client binding.
#
# Temporal activities are stateless functions; the execution-manager client is
# injected via ``bind_execution_client`` at worker registration (and in tests),
# keeping the workflow deterministic while letting the activities reach the
# execution-manager HTTP API.
# ---------------------------------------------------------------------------

_client: ExecutionManagerClient | None = None


def bind_execution_client(client: ExecutionManagerClient | None) -> None:
    """Set the execution-manager client used by the pipeline activities."""
    global _client
    _client = client


def _get_client() -> ExecutionManagerClient:
    if _client is None:
        raise RuntimeError("execution-manager client is not bound")
    return _client


@_workflow.defn(name=EXECUTION_WORKFLOW_NAME)
class ExecutionRunWorkflow:
    """Durable pipeline that runs a task's coding session to completion."""

    _is_cancelled: bool = False

    @_workflow.run
    async def run(self, submission: ExecutionRunSubmission) -> ExecutionRunResult:
        if self._is_cancelled:
            return ExecutionRunResult(
                execution_id=submission.execution_id, status="cancelled"
            )

        try:
            await self._call(provision, submission)
            await self._call(prepare, submission)
            await self._call(start_session, submission)
            outcome: RunOutcome = await _workflow.execute_activity(
                run_task,
                args=[submission],
                retry_policy=self._retry_policy(),
                start_to_close_timeout=timedelta(
                    seconds=RUN_ACTIVITY_TIMEOUT_SECONDS
                ),
            )
        except Exception as exc:  # noqa: BLE001 - any activity failure fails the run
            return ExecutionRunResult(
                execution_id=submission.execution_id,
                status="failed",
                message=str(exc),
            )

        if not outcome.ok:
            return ExecutionRunResult(
                execution_id=submission.execution_id,
                status="failed",
                message=outcome.error or "agent task failed",
            )
        return ExecutionRunResult(
            execution_id=submission.execution_id, status="succeeded"
        )

    async def _call(
        self,
        activity: object,
        submission: ExecutionRunSubmission,
    ) -> str:
        return await _workflow.execute_activity(
            activity,
            args=[submission],
            retry_policy=self._retry_policy(),
            start_to_close_timeout=timedelta(seconds=RUN_ACTIVITY_TIMEOUT_SECONDS),
        )

    def _retry_policy(self) -> RetryPolicy:
        return RetryPolicy(
            maximum_attempts=MAX_RUN_RETRIES,
            initial_interval=timedelta(seconds=RUN_RETRY_BACKOFF_SECONDS),
            backoff_coefficient=RUN_RETRY_BACKOFF_MULTIPLIER,
        )

    @_workflow.signal
    async def cancel(self) -> None:
        self._is_cancelled = True


@_activity.defn
async def provision(submission: ExecutionRunSubmission) -> str:
    """Provision the workspace container and return its new status."""
    return _get_client().provision_execution(submission.execution_id)


@_activity.defn
async def prepare(submission: ExecutionRunSubmission) -> str:
    """Clone/checkout the repository and return the new status."""
    return _get_client().prepare_execution(submission.execution_id)


@_activity.defn
async def start_session(submission: ExecutionRunSubmission) -> str:
    """Start the coding session and return the new status."""
    return _get_client().start_session(submission.execution_id)


@_activity.defn
async def run_task(submission: ExecutionRunSubmission) -> RunOutcome:
    """Run the task prompt through the coding agent."""
    return _get_client().run_execution(submission.execution_id, submission.prompt)
