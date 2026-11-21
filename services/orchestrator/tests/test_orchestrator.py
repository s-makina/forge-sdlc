"""Tests for the orchestrator service (Phase 4.1)."""

from app.services.orchestrator import Orchestrator, WorkflowSubmission
from app.temporal.client import MemoryTemporalClient


def _submission(workflow_id: int = 1) -> WorkflowSubmission:
    return WorkflowSubmission(
        workflow_id=workflow_id,
        project_id=1,
        template_slug="feature-development",
        inputs={"feature": "login"},
    )


def test_start_submits_durable_run(orchestrator: Orchestrator) -> None:
    run = orchestrator.start(_submission(1))
    assert run.workflow_id == "workflow-1"
    assert run.status == "running"


def test_durable_id_is_stable() -> None:
    assert _submission(7).durable_id == "workflow-7"


def test_cancel_requests_cancellation(orchestrator: Orchestrator) -> None:
    orchestrator.start(_submission(1))
    orchestrator.cancel(1)
    assert orchestrator.status(1) == "cancelled"


def test_health_uses_client(orchestrator: Orchestrator) -> None:
    assert orchestrator.healthy() is True


def test_status_unknown_before_start(orchestrator: Orchestrator) -> None:
    assert orchestrator.status(99) == ""


def test_memory_client_records_run(
    orchestrator: Orchestrator, temporal_client: MemoryTemporalClient
) -> None:
    orchestrator.start(_submission(1))
    assert "workflow-1" in temporal_client._runs
    assert temporal_client._runs["workflow-1"].status == "running"