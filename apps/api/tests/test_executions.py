"""Execution route tests (Phase 4.4/4.6)."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.container import get_container
from app.core.security import codec, hash_password
from app.models.project import Project
from app.models.user import User
from app.schemas.tasks import TaskCreate
from app.services import tasks


@pytest.fixture(autouse=True)
def _reset_container() -> None:
    """Drop any fake execution-manager/orchestrator clients between tests."""
    get_container().unregister("execution_manager_client")
    get_container().unregister("orchestrator_client")


def _login(client: TestClient, db: Session) -> None:
    user = User(
        email="exec@example.com",
        password_hash=hash_password("secret"),
        display_name="Exec",
        is_active=True,
        is_operator=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    client.cookies.set(get_settings().session_cookie_name, codec.create(user.id))


def _project(db: Session) -> int:
    project = Project(name="Exec Project")
    db.add(project)
    db.commit()
    db.refresh(project)
    return project.id


def _launched_task(db: Session, project_id: int) -> int:
    task = tasks.create_task(
        db,
        TaskCreate(
            project_id=project_id,
            title="Snake Game Build",
            description="Build the snake game",
            task_type="feature",
            repository_url="https://github.com/example/snake.git",
            model_profile="coding-strong",
            assigned_role="software_engineer",
        ),
    )
    tasks.transition_status(db, task, "ready")
    task.last_execution_id = "exec-snake-1"
    task.last_execution_status = "running"
    db.commit()
    return task.id


class _FakeResponse:
    def __init__(self, status_code: int, data: dict) -> None:
        self.status_code = status_code
        self._data = data
        self.text = None

    def json(self) -> dict:
        return self._data


class _FakeStatusClient:
    """Fake execution-manager/orchestrator client exposing ``get(url, headers).``"""

    def __init__(
        self,
        *,
        status_code: int = 200,
        data: dict | None = None,
        exc: Exception | None = None,
    ) -> None:
        self.status_code = status_code
        self.data = data or {}
        self.exc = exc
        self.calls: list[dict] = []

    def get(self, url: str, headers: dict | None = None):
        self.calls.append({"url": url, "headers": headers})
        if self.exc is not None:
            raise self.exc
        return _FakeResponse(self.status_code, self.data)


def test_list_requires_auth(client: TestClient) -> None:
    res = client.get("/api/v1/executions")
    assert res.status_code == 401


def test_list_executions_derived_from_tasks(
    client: TestClient, db_session: Session
) -> None:
    _login(client, db_session)
    project_id = _project(db_session)
    _launched_task(db_session, project_id)
    # A task without an execution must not appear.
    tasks.create_task(
        db_session,
        TaskCreate(
            project_id=project_id,
            title="No execution yet",
            task_type="documentation",
            model_profile="coding-strong",
            assigned_role="software_engineer",
        ),
    )

    res = client.get("/api/v1/executions")

    assert res.status_code == 200
    body = res.json()
    assert len(body["items"]) == 1
    item = body["items"][0]
    assert item["execution_id"] == "exec-snake-1"
    assert item["task_title"] == "Snake Game Build"
    assert item["status"] == "running"


def test_execution_status_proxies_to_execution_manager(
    client: TestClient, db_session: Session
) -> None:
    _login(client, db_session)
    fake = _FakeStatusClient(status_code=200, data={"status": "succeeded"})
    get_container().register("execution_manager_client", fake)

    res = client.get("/api/v1/executions/exec-snake-1/status")

    assert res.status_code == 200
    assert res.json() == {"execution_id": "exec-snake-1", "status": "succeeded"}
    assert fake.calls[0]["url"].endswith("/executions/exec-snake-1/status")


def test_execution_status_degrades_to_unknown(
    client: TestClient, db_session: Session
) -> None:
    _login(client, db_session)
    get_container().register(
        "execution_manager_client", _FakeStatusClient(exc=ConnectionError("down"))
    )

    res = client.get("/api/v1/executions/exec-snake-1/status")

    assert res.status_code == 200
    assert res.json() == {"execution_id": "exec-snake-1", "status": "unknown"}


def test_execution_run_status_proxies_to_orchestrator(
    client: TestClient, db_session: Session
) -> None:
    _login(client, db_session)
    fake = _FakeStatusClient(
        status_code=200, data={"execution_id": "exec-snake-1", "durable_status": "running"}
    )
    get_container().register("orchestrator_client", fake)

    res = client.get("/api/v1/executions/exec-snake-1/run-status")

    assert res.status_code == 200
    assert res.json() == {
        "execution_id": "exec-snake-1",
        "durable_status": "running",
    }
    assert fake.calls[0]["url"].endswith("/executions/exec-snake-1/run-status")


def test_execution_run_status_degrades_to_unknown(
    client: TestClient, db_session: Session
) -> None:
    _login(client, db_session)
    get_container().register(
        "orchestrator_client", _FakeStatusClient(exc=ConnectionError("down"))
    )

    res = client.get("/api/v1/executions/exec-snake-1/run-status")

    assert res.status_code == 200
    assert res.json() == {"execution_id": "exec-snake-1", "durable_status": "unknown"}


def test_execution_logs_proxies_to_execution_manager(
    client: TestClient, db_session: Session
) -> None:
    _login(client, db_session)
    fake = _FakeStatusClient(
        status_code=200,
        data={
            "execution_id": "exec-snake-1",
            "entries": [
                {
                    "sequence": 1,
                    "timestamp": "2026-11-24T06:00:00+00:00",
                    "kind": "command",
                    "level": "info",
                    "message": "git checkout -b snake-game",
                },
                {
                    "sequence": 2,
                    "timestamp": "2026-11-24T06:01:00+00:00",
                    "kind": "tool_call",
                    "level": "info",
                    "message": "edit_file(src/snake.py)",
                },
            ],
        },
    )
    get_container().register("execution_manager_client", fake)

    res = client.get("/api/v1/executions/exec-snake-1/logs")

    assert res.status_code == 200
    body = res.json()
    assert body["execution_id"] == "exec-snake-1"
    assert len(body["entries"]) == 2
    assert body["entries"][0]["kind"] == "command"
    assert body["entries"][0]["message"] == "git checkout -b snake-game"
    assert body["entries"][1]["kind"] == "tool_call"
    assert fake.calls[0]["url"].endswith("/executions/exec-snake-1/logs")


def test_execution_logs_degrades_to_empty(
    client: TestClient, db_session: Session
) -> None:
    _login(client, db_session)
    get_container().register(
        "execution_manager_client", _FakeStatusClient(exc=ConnectionError("down"))
    )

    res = client.get("/api/v1/executions/exec-snake-1/logs")

    assert res.status_code == 200
    assert res.json() == {"execution_id": "exec-snake-1", "entries": []}


def test_execution_artefacts_proxies_to_execution_manager(
    client: TestClient, db_session: Session
) -> None:
    _login(client, db_session)
    fake = _FakeStatusClient(
        status_code=200,
        data={
            "execution_id": "exec-snake-1",
            "artefacts": [
                {
                    "name": "snake.patch",
                    "location": "artifacts/executions/exec-snake-1/snake.patch",
                    "size_bytes": 1234,
                    "mime_type": "text/x-patch",
                    "kind": "diff",
                },
                {
                    "name": "report.xml",
                    "location": "artifacts/executions/exec-snake-1/report.xml",
                    "size_bytes": 567,
                    "mime_type": "application/xml",
                    "kind": "test_report",
                },
            ],
        },
    )
    get_container().register("execution_manager_client", fake)

    res = client.get("/api/v1/executions/exec-snake-1/artefacts")

    assert res.status_code == 200
    body = res.json()
    assert body["execution_id"] == "exec-snake-1"
    assert len(body["artefacts"]) == 2
    assert body["artefacts"][0]["name"] == "snake.patch"
    assert body["artefacts"][0]["size_bytes"] == 1234
    assert body["artefacts"][0]["kind"] == "diff"
    assert body["artefacts"][1]["kind"] == "test_report"
    assert fake.calls[0]["url"].endswith("/executions/exec-snake-1/artefacts")


def test_execution_artefacts_degrades_to_empty(
    client: TestClient, db_session: Session
) -> None:
    _login(client, db_session)
    get_container().register(
        "execution_manager_client", _FakeStatusClient(exc=ConnectionError("down"))
    )

    res = client.get("/api/v1/executions/exec-snake-1/artefacts")

    assert res.status_code == 200
    assert res.json() == {"execution_id": "exec-snake-1", "artefacts": []}
