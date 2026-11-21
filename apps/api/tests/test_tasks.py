"""Task endpoint tests for Phase 4.3."""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import codec, hash_password
from app.models.user import User
from app.schemas.tasks import TaskCreate
from app.services import tasks


def _login(client: TestClient, db: Session, email: str = "task@example.com") -> User:
    user = User(
        email=email,
        password_hash=hash_password("secret"),
        display_name="Tester",
        is_active=True,
        is_operator=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    client.cookies.set(get_settings().session_cookie_name, codec.create(user.id))
    return user


def _make_task(db: Session, project_id: int = 1, **overrides) -> int:
    payload: dict = {
        "project_id": project_id,
        "title": "Implement login",
        "description": "Add authentication",
        "task_type": "feature",
    }
    payload.update(overrides)
    task = tasks.create_task(db, TaskCreate(**payload))
    return task.id


def test_create_and_list_task(client: TestClient, db_session: Session) -> None:
    _login(client, db_session)
    res = client.post(
        "/api/v1/tasks",
        json={"project_id": 1, "title": "Implement login", "task_type": "feature"},
    )
    assert res.status_code == 201
    body = res.json()
    assert body["status"] == "draft"
    assert body["task_type"] == "feature"

    listing = client.get("/api/v1/tasks").json()
    assert listing["total"] == 1


def test_task_dependencies(client: TestClient, db_session: Session) -> None:
    _login(client, db_session)
    first = client.post(
        "/api/v1/tasks", json={"project_id": 1, "title": "Schema"}
    ).json()
    second = client.post(
        "/api/v1/tasks",
        json={"project_id": 1, "title": "Service", "dependencies": [first["id"]]},
    ).json()

    assert second["dependencies"] == [first["id"]]


def test_task_self_dependency_rejected(client: TestClient, db_session: Session) -> None:
    _login(client, db_session)
    created = client.post("/api/v1/tasks", json={"project_id": 1, "title": "Only"}).json()
    res = client.post(
        f"/api/v1/tasks/{created['id']}/dependencies", json={"depends_on": [created["id"]]}
    )
    assert res.status_code == 422


def test_status_lifecycle_enforced(client: TestClient, db_session: Session) -> None:
    _login(client, db_session)
    task_id = _make_task(db_session)
    res = client.post(f"/api/v1/tasks/{task_id}/status", json={"status": "in_progress"})
    assert res.status_code == 200
    assert res.json()["status"] == "in_progress"
    assert res.json()["started_at"] is not None

    res = client.post(f"/api/v1/tasks/{task_id}/status", json={"status": "completed"})
    assert res.status_code == 200
    assert res.json()["status"] == "completed"
    assert res.json()["finished_at"] is not None

    # Terminal tasks cannot transition further.
    res = client.post(f"/api/v1/tasks/{task_id}/status", json={"status": "blocked"})
    assert res.status_code == 409


def test_task_dependencies_satisfied_service(db_session: Session) -> None:
    dep_id = _make_task(db_session, title="Dep")
    task_id = _make_task(db_session, title="Main", dependencies=[dep_id])
    dep = tasks.get_task(db_session, dep_id)
    main = tasks.get_task(db_session, task_id)
    assert dep is not None and main is not None

    assert tasks.dependencies_satisfied(db_session, main) is False
    tasks.transition_status(db_session, dep, "completed")
    assert tasks.dependencies_satisfied(db_session, main) is True