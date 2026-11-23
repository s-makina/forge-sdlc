"""Router tests for the orchestrator worker (Phase 4.1)."""

from fastapi.testclient import TestClient

from app.services.orchestrator import ExecutionRunSubmission


def test_health(client: TestClient) -> None:
    res = client.get("/health")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok"
    assert body["temporal"] is True


def test_start_and_query_workflow(client: TestClient) -> None:
    res = client.post(
        "/api/v1/workflows/1/start",
        json={
            "workflow_id": 1,
            "project_id": 10,
            "template_slug": "feature-development",
            "inputs": {"feature": "login"},
        },
    )
    assert res.status_code == 200
    assert res.json()["durable_status"] == "running"

    status = client.get("/api/v1/workflows/1/status").json()
    assert status["durable_status"] == "running"


def test_cancel_workflow(client: TestClient) -> None:
    client.post(
        "/api/v1/workflows/2/start",
        json={"workflow_id": 2, "project_id": 10, "template_slug": "bug-fix", "inputs": {}},
    )
    res = client.post("/api/v1/workflows/2/cancel")
    assert res.status_code == 200
    assert res.json()["durable_status"] == "cancelled"


def test_workflow_id_mismatch_rejected(client: TestClient) -> None:
    res = client.post(
        "/api/v1/workflows/1/start",
        json={"workflow_id": 999, "project_id": 10, "template_slug": "feature-development"},
    )
    assert res.status_code == 422


def test_status_unknown(client: TestClient) -> None:
    body = client.get("/api/v1/workflows/77/status").json()
    assert body["durable_status"] == ""


def test_start_execution_run_and_query_status(client: TestClient) -> None:
    res = client.post(
        "/api/v1/executions/exec-abc/start-run",
        json={
            "execution_id": "exec-abc",
            "task_id": "7",
            "project_id": 10,
            "prompt": "add a README",
        },
    )
    assert res.status_code == 200
    body = res.json()
    assert body["execution_id"] == "exec-abc"
    assert body["durable_status"] == "running"

    status = client.get("/api/v1/executions/exec-abc/run-status").json()
    assert status["durable_status"] == "running"


def test_execution_run_id_mismatch_rejected(client: TestClient) -> None:
    res = client.post(
        "/api/v1/executions/exec-abc/start-run",
        json={"execution_id": "other", "project_id": 10},
    )
    assert res.status_code == 422


def test_execution_run_status_unknown(client: TestClient) -> None:
    body = client.get("/api/v1/executions/exec-missing/run-status").json()
    assert body["durable_status"] == ""


def test_cancel_execution_run(client: TestClient) -> None:
    res = client.post(
        "/api/v1/executions/exec-abc/start-run",
        json={"execution_id": "exec-abc", "project_id": 10},
    )
    assert res.status_code == 200
    cancel = client.post("/api/v1/executions/exec-abc/cancel-run")
    assert cancel.status_code == 200
    assert cancel.json()["durable_status"] == "cancelled"


def test_execution_run_submission_durable_id() -> None:
    sub = ExecutionRunSubmission(execution_id="exec-abc")
    assert sub.durable_id == "execution-exec-abc"
