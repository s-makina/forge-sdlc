"""Router tests for the orchestrator worker (Phase 4.1)."""

from fastapi.testclient import TestClient


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