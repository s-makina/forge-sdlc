"""Explicit task-launch endpoint tests (Phase 3/4 UI wiring)."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.container import get_container
from app.core.security import codec, hash_password
from app.models.project import Project, Repository
from app.models.user import User
from app.schemas.tasks import TaskCreate
from app.services import tasks


@pytest.fixture(autouse=True)
def _reset_container() -> None:
    """Drop any fake execution-manager client between tests."""
    get_container().unregister("execution_manager_client")


def _login(client: TestClient, db: Session) -> None:
    user = User(
        email="launch@example.com",
        password_hash=hash_password("secret"),
        display_name="Launcher",
        is_active=True,
        is_operator=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    client.cookies.set(get_settings().session_cookie_name, codec.create(user.id))


def _project_with_repo(db: Session, *, url: str = "https://github.com/example/app.git") -> int:
    project = Project(name="Launch Project")
    db.add(project)
    db.flush()
    db.add(Repository(project_id=project.id, url=url, default_branch="main"))
    db.commit()
    db.refresh(project)
    return project.id


def _ready_task(db: Session, project_id: int, **overrides) -> int:
    payload: dict = {
        "project_id": project_id,
        "title": "Add a README",
        "description": "Write setup instructions",
        "task_type": "documentation",
        "repository_url": "https://github.com/example/app.git",
        "model_profile": "coding-strong",
        "assigned_role": "software_engineer",
    }
    payload.update(overrides)
    task = tasks.create_task(db, TaskCreate(**payload))
    tasks.transition_status(db, task, "ready")
    return task.id


class _FakeResponse:
    def __init__(self, status_code: int, data: dict) -> None:
        self.status_code = status_code
        self._data = data
        self.text = None

    def json(self) -> dict:
        return self._data


class _FakeClient:
    """A fake ``http_client`` exposing ``post(url, json, headers)``."""

    def __init__(self, *, status_code: int = 201, data: dict | None = None, exc: Exception | None = None) -> None:
        self.status_code = status_code
        self.data = data or {"execution_id": "exec-abc", "status": "created"}
        self.exc = exc
        self.calls: list[dict] = []

    def post(self, url: str, json: dict | None = None, headers: dict | None = None):
        self.calls.append({"url": url, "json": json, "headers": headers})
        if self.exc is not None:
            raise self.exc
        return _FakeResponse(self.status_code, self.data)


def test_launch_ready_task_creates_execution(client: TestClient, db_session: Session) -> None:
    _login(client, db_session)
    project_id = _project_with_repo(db_session)
    task_id = _ready_task(db_session, project_id)

    fake = _FakeClient()
    get_container().register("execution_manager_client", fake)

    res = client.post(f"/api/v1/tasks/{task_id}/execute")

    assert res.status_code == 200
    body = res.json()
    assert body["execution_id"] == "exec-abc"
    assert body["task_id"] == task_id
    assert body["status"] == "in_progress"
    task = tasks.get_task(db_session, task_id)
    assert task is not None
    assert task.status == "in_progress"
    assert task.last_execution_id == "exec-abc"
    assert task.last_execution_status == "created"
    # The worker must receive the registered repository only (no arbitrary clones).
    sent = fake.calls[0]
    assert sent["json"]["repository_url"] == "https://github.com/example/app.git"
    assert sent["headers"]["X-ForgeSDLC-Token"]


def test_launch_rejects_unregistered_repository(
    client: TestClient, db_session: Session
) -> None:
    _login(client, db_session)
    project_id = _project_with_repo(db_session, url="https://github.com/example/app.git")
    task_id = _ready_task(
        db_session,
        project_id,
        repository_url="https://github.com/untrusted/other.git",
    )

    res = client.post(f"/api/v1/tasks/{task_id}/execute")

    assert res.status_code == 409
    assert "not registered" in res.json()["error"]["message"]


def test_launch_rejects_draft_task(client: TestClient, db_session: Session) -> None:
    _login(client, db_session)
    project_id = _project_with_repo(db_session)
    task_id = _ready_task(db_session, project_id)
    tasks.transition_status(db_session, tasks.get_task(db_session, task_id), "draft")

    res = client.post(f"/api/v1/tasks/{task_id}/execute")

    assert res.status_code == 409


def test_launch_returns_503_when_manager_unavailable(
    client: TestClient, db_session: Session
) -> None:
    _login(client, db_session)
    project_id = _project_with_repo(db_session)
    task_id = _ready_task(db_session, project_id)

    get_container().register(
        "execution_manager_client", _FakeClient(exc=ConnectionError("boom"))
    )

    res = client.post(f"/api/v1/tasks/{task_id}/execute")

    assert res.status_code == 503
    task = tasks.get_task(db_session, task_id)
    assert task is not None
    assert task.status == "ready"
