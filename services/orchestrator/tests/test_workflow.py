"""Tests for the durable Temporal feature-development workflow (Phase 4.1/4.6).

These run against Temporal's in-process dev-server test environment
(``WorkflowEnvironment``), which drives the decorated workflow and its
activities without a live production server. They are skipped when the Temporal
dev-server binary is unavailable.
"""

import asyncio

import pytest

from app.services.orchestrator import WorkflowSubmission
from app.temporal import worker

pytestmark = pytest.mark.skipif(
    not pytest.importorskip("temporalio.testing").WorkflowEnvironment,
    reason="Temporal test environment unavailable",
)

TASK_QUEUE = "forgesdlc-workflows"


def _submission(workflow_id: int = 1) -> WorkflowSubmission:
    return WorkflowSubmission(
        workflow_id=workflow_id,
        project_id=1,
        template_slug="feature-development",
        inputs={"feature": "login"},
    )


async def _run(scenario):
    from temporalio.testing import WorkflowEnvironment
    from temporalio.worker import Worker

    async with await WorkflowEnvironment.start_local() as env:
        async with Worker(
            env.client,
            task_queue=TASK_QUEUE,
            workflows=[worker.FeatureDevelopmentWorkflow],
            activities=[worker.run_stage],
        ):
            await scenario(env)


def test_workflow_runs_all_stages_to_success() -> None:
    async def scenario(env) -> None:
        handle = await env.client.start_workflow(
            worker.FeatureDevelopmentWorkflow,
            arg=_submission(1),
            id="workflow-1",
            task_queue=TASK_QUEUE,
        )
        result = await handle.result()
        assert result.status == "succeeded"
        assert result.completed_stages == worker.FEATURE_DEVELOPMENT_STAGES

    asyncio.run(_run(scenario))


def test_workflow_is_cancellable() -> None:
    async def scenario(env) -> None:
        handle = await env.client.start_workflow(
            worker.FeatureDevelopmentWorkflow,
            arg=_submission(2),
            id="workflow-2",
            task_queue=TASK_QUEUE,
        )
        await handle.signal(worker.FeatureDevelopmentWorkflow.cancel)
        result = await handle.result()
        assert result.status == "cancelled"

    asyncio.run(_run(scenario))


def test_run_stage_returns_success() -> None:
    async def scenario() -> None:
        outcome = await worker.run_stage(_submission(), "requirements")
        assert outcome.ok is True
        assert outcome.stage == "requirements"

    asyncio.run(scenario())
