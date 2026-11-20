"""Execution service and API tests for subphase 3.1."""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.execution import Execution, ExecutionStatus
from app.services import executions


def _payload(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "project_id": 1,
        "task_id": "task-1",
        "repository_url": "https://github.com/example/app.git",
        "branch": "main",
    }
    base.update(overrides)
    return base


def test_create_execution(client: TestClient, db_session: Session) -> None:
    res = client.post("/api/v1/executions", json=_payload())
    assert res.status_code == 201
    body = res.json()
    assert body["status"] == ExecutionStatus.CREATED.value
    assert body["project_id"] == 1
    assert body["repository_url"] == "https://github.com/example/app.git"
    assert body["image"] == "python:3.12-slim"
    assert body["cpu_limit"] == 1.0


def test_create_execution_with_overrides(client: TestClient, db_session: Session) -> None:
    res = client.post(
        "/api/v1/executions",
        json=_payload(image="node:20-slim", timeout_seconds=120),
    )
    assert res.status_code == 201
    body = res.json()
    assert body["image"] == "node:20-slim"
    assert body["timeout_seconds"] == 120


def test_execution_ids_unique(client: TestClient, db_session: Session) -> None:
    first = client.post("/api/v1/executions", json=_payload()).json()
    second = client.post("/api/v1/executions", json=_payload()).json()
    assert first["execution_id"] != second["execution_id"]


def test_get_execution_and_status(client: TestClient, db_session: Session) -> None:
    created = client.post("/api/v1/executions", json=_payload()).json()
    execution_id = created["execution_id"]

    res = client.get(f"/api/v1/executions/{execution_id}")
    assert res.status_code == 200
    assert res.json()["execution_id"] == execution_id

    res = client.get(f"/api/v1/executions/{execution_id}/status")
    assert res.status_code == 200
    assert res.json()["status"] == ExecutionStatus.CREATED.value


def test_get_execution_not_found(client: TestClient, db_session: Session) -> None:
    assert client.get("/api/v1/executions/does-not-exist").status_code == 404


def test_list_executions_filter_by_project(client: TestClient, db_session: Session) -> None:
    client.post("/api/v1/executions", json=_payload(project_id=1))
    client.post("/api/v1/executions", json=_payload(project_id=2))

    res = client.get("/api/v1/executions?project_id=1")
    assert res.status_code == 200
    body = res.json()
    assert body["total"] == 1
    assert all(item["project_id"] == 1 for item in body["items"])


def test_cancel_execution(client: TestClient, db_session: Session) -> None:
    created = client.post("/api/v1/executions", json=_payload()).json()
    execution_id = created["execution_id"]

    res = client.post(f"/api/v1/executions/{execution_id}/cancel")
    assert res.status_code == 200
    assert res.json()["requested"] is True
    assert res.json()["status"] == ExecutionStatus.CANCELLED.value


def test_cleanup_execution(client: TestClient, db_session: Session) -> None:
    created = client.post("/api/v1/executions", json=_payload()).json()
    execution_id = created["execution_id"]
    client.post(f"/api/v1/executions/{execution_id}/cancel")

    res = client.post(f"/api/v1/executions/{execution_id}/cleanup")
    assert res.status_code == 200
    assert res.json()["cleaned"] is True
    assert res.json()["status"] == ExecutionStatus.DONE.value


def test_cleanup_rejected_while_running(client: TestClient, db_session: Session) -> None:
    created = client.post("/api/v1/executions", json=_payload()).json()
    execution_id = created["execution_id"]

    res = client.post(f"/api/v1/executions/{execution_id}/cleanup")
    assert res.status_code == 409


def test_transition_records_start_and_finish(client: TestClient, db_session: Session) -> None:
    created = client.post("/api/v1/executions", json=_payload()).json()
    execution_id = created["execution_id"]

    execution = executions.get_execution(db_session, execution_id)
    assert execution is not None

    executions.transition(db_session, execution, ExecutionStatus.RUNNING)
    assert execution.started_at is not None

    executions.transition(db_session, execution, ExecutionStatus.SUCCEEDED)
    assert execution.finished_at is not None


def test_count_active_executions(client: TestClient, db_session: Session) -> None:
    client.post("/api/v1/executions", json=_payload())
    client.post("/api/v1/executions", json=_payload())
    assert executions.count_active_executions(db_session) == 2


def test_logs_and_artefacts_empty_placeholders(
    client: TestClient, db_session: Session
) -> None:
    created = client.post("/api/v1/executions", json=_payload()).json()
    execution_id = created["execution_id"]

    logs = client.get(f"/api/v1/executions/{execution_id}/logs")
    assert logs.status_code == 200
    assert logs.json()["entries"] == []

    artefacts = client.get(f"/api/v1/executions/{execution_id}/artefacts")
    assert artefacts.status_code == 200
    assert artefacts.json()["artefacts"] == []