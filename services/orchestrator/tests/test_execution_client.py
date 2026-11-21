"""Tests for the execution-manager client (Phase 4.4/4.6)."""

from app.execution.client import ExecutionRequest, MemoryExecutionManagerClient
from app.services.orchestrator import Orchestrator
from app.temporal.client import MemoryTemporalClient


def test_memory_client_requests_execution() -> None:
    client = MemoryExecutionManagerClient()
    handle = client.request_execution(
        ExecutionRequest(project_id=1, task_id="2", branch="task/2")
    )
    assert handle.execution_id == "exec-1"
    assert handle.status == "created"
    assert client.execution_status("exec-1") == "created"


def test_memory_client_unknown_execution_returns_empty() -> None:
    client = MemoryExecutionManagerClient()
    assert client.execution_status("exec-missing") == ""


def test_memory_client_cancel_updates_status() -> None:
    client = MemoryExecutionManagerClient()
    handle = client.request_execution(ExecutionRequest(project_id=1))
    client.cancel_execution(handle.execution_id)
    assert client.execution_status(handle.execution_id) == "cancelled"


def test_memory_client_health_reflects_set_healthy() -> None:
    client = MemoryExecutionManagerClient()
    assert client.health() is True
    client.set_healthy(False)
    assert client.health() is False


def test_orchestrator_requests_execution_via_manager() -> None:
    temporal = MemoryTemporalClient()
    execution_manager = MemoryExecutionManagerClient()
    orchestrator = Orchestrator(
        temporal,
        task_queue="forgesdlc-workflows",
        timeout_seconds=3600,
        execution_manager=execution_manager,
    )
    execution_id = orchestrator.request_execution(
        ExecutionRequest(project_id=1, task_id="7", branch="task/7")
    )
    assert execution_id == "exec-1"
    assert orchestrator.execution_status(execution_id) == "created"


def test_orchestrator_unknown_execution_status_is_empty() -> None:
    temporal = MemoryTemporalClient()
    execution_manager = MemoryExecutionManagerClient()
    orchestrator = Orchestrator(
        temporal,
        task_queue="q",
        timeout_seconds=3600,
        execution_manager=execution_manager,
    )
    assert orchestrator.execution_status("exec-missing") == ""
