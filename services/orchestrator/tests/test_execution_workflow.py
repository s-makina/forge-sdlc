"""Tests for the durable execution-run workflow (Phase 4.4/4.6).

These run against Temporal's in-process dev-server test environment
(``WorkflowEnvironment``), driving the decorated workflow and its activities
against an in-memory execution-manager fake. They are skipped when the Temporal
dev-server binary is unavailable.
"""

import asyncio

import pytest

from app.execution.client import ExecutionRequest, MemoryExecutionManagerClient
from app.services.orchestrator import ExecutionRunSubmission
from app.temporal import execution_workflow as ew

pytestmark = pytest.mark.skipif(
    not pytest.importorskip("temporalio.testing").WorkflowEnvironment,
    reason="Temporal test environment unavailable",
)

TASK_QUEUE = "forgesdlc-workflows"


def _submission(execution_id: str = "exec-1", prompt: str = "add a README") -> ExecutionRunSubmission:
    return ExecutionRunSubmission(
        execution_id=execution_id,
        task_id="7",
        project_id=1,
        prompt=prompt,
    )


async def _run(scenario, client: MemoryExecutionManagerClient):
    from temporalio.testing import WorkflowEnvironment
    from temporalio.worker import Worker

    ew.bind_execution_client(client)
    try:
        async with await WorkflowEnvironment.start_local() as env:
            async with Worker(
                env.client,
                task_queue=TASK_QUEUE,
                workflows=[ew.ExecutionRunWorkflow],
                activities=[ew.provision, ew.prepare, ew.start_session, ew.run_task],
            ):
                await scenario(env, client)
    finally:
        ew.bind_execution_client(None)


def test_workflow_runs_pipeline_to_success() -> None:
    client = MemoryExecutionManagerClient()

    async def scenario(env, client) -> None:
        handle = client.request_execution(ExecutionRequest(project_id=1, task_id="7"))
        sub = ExecutionRunSubmission(
            execution_id=handle.execution_id,
            task_id="7",
            project_id=1,
            prompt="add a README",
        )
        wf = await env.client.start_workflow(
            ew.ExecutionRunWorkflow,
            arg=sub,
            id=sub.durable_id,
            task_queue=TASK_QUEUE,
        )
        result = await wf.result()
        assert result.status == "succeeded"
        assert result.execution_id == sub.execution_id
        # The pipeline advanced provision -> prepare -> start-session -> run.
        assert client.execution_status(sub.execution_id) == "succeeded"
        assert client._prompts.get(sub.execution_id) == ["add a README"]

    asyncio.run(_run(scenario, client))


def test_workflow_is_cancellable() -> None:
    client = MemoryExecutionManagerClient()

    async def scenario(env, client) -> None:
        sub = _submission()
        handle = await env.client.start_workflow(
            ew.ExecutionRunWorkflow,
            arg=sub,
            id=sub.durable_id,
            task_queue=TASK_QUEUE,
        )
        await handle.signal(ew.ExecutionRunWorkflow.cancel)
        result = await handle.result()
        assert result.status == "cancelled"

    asyncio.run(_run(scenario, client))
