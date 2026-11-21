"""Tests for the in-memory Temporal client (Phase 4.1)."""

from app.temporal.client import MemoryTemporalClient


def test_start_and_query_status() -> None:
    client = MemoryTemporalClient()
    run = client.start_workflow(
        name="forgesdlc_feature_development",
        workflow_id="workflow-1",
        task_queue="forgesdlc-workflows",
        args=[],
        timeout_seconds=3600,
    )
    assert run.workflow_id == "workflow-1"
    assert run.run_id == "run-workflow-1"
    assert client.workflow_status("workflow-1") == "running"


def test_cancel_updates_status() -> None:
    client = MemoryTemporalClient()
    client.start_workflow(
        name="wf",
        workflow_id="workflow-2",
        task_queue="q",
        args=[],
        timeout_seconds=3600,
    )
    client.cancel_workflow("workflow-2")
    assert client.workflow_status("workflow-2") == "cancelled"


def test_unknown_workflow_returns_empty() -> None:
    client = MemoryTemporalClient()
    assert client.workflow_status("workflow-missing") == ""


def test_health_reflects_set_healthy() -> None:
    client = MemoryTemporalClient()
    assert client.health() is True
    client.set_healthy(False)
    assert client.health() is False