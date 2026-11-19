"""Project endpoint tests."""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import codec, hash_password
from app.models.user import User


def _login(client: TestClient, db: Session, email: str = "test@example.com") -> User:
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


def test_create_and_list_project(client: TestClient, db_session: Session) -> None:
    _login(client, db_session)

    res = client.post(
        "/api/v1/projects",
        json={"name": "Appointment SaaS", "description": "Demo project"},
    )
    assert res.status_code == 201
    project = res.json()
    assert project["name"] == "Appointment SaaS"
    assert project["is_active"] is True

    res = client.get("/api/v1/projects")
    assert res.status_code == 200
    body = res.json()
    assert body["total"] == 1
    assert body["items"][0]["name"] == "Appointment SaaS"


def test_create_project_with_repository(client: TestClient, db_session: Session) -> None:
    _login(client, db_session)
    res = client.post(
        "/api/v1/projects",
        json={
            "name": "With Repo",
            "repositories": [
                {"url": "https://github.com/example/app.git", "default_branch": "main"}
            ],
        },
    )
    assert res.status_code == 201
    project = res.json()
    assert len(project["repositories"]) == 1
    assert project["repositories"][0]["url"] == "https://github.com/example/app.git"


def test_audit_record_on_create(client: TestClient, db_session: Session) -> None:
    _login(client, db_session)
    client.post("/api/v1/projects", json={"name": "Second"})

    res = client.get("/api/v1/audit")
    assert res.status_code == 200
    body = res.json()
    assert body["total"] == 1
    assert body["items"][0]["action"] == "project.create"


def test_audit_record_on_update(client: TestClient, db_session: Session) -> None:
    _login(client, db_session)
    created = client.post("/api/v1/projects", json={"name": "Original"}).json()
    res = client.patch(f"/api/v1/projects/{created['id']}", json={"is_active": False})
    assert res.status_code == 200
    assert res.json()["is_active"] is False

    actions = [item["action"] for item in client.get("/api/v1/audit").json()["items"]]
    assert "project.update" in actions


def test_add_repository_audited(client: TestClient, db_session: Session) -> None:
    _login(client, db_session)
    created = client.post("/api/v1/projects", json={"name": "Repo Host"}).json()
    res = client.post(
        f"/api/v1/projects/{created['id']}/repositories",
        json={"url": "https://github.com/example/other.git"},
    )
    assert res.status_code == 201
    assert res.json()["url"] == "https://github.com/example/other.git"

    actions = [item["action"] for item in client.get("/api/v1/audit").json()["items"]]
    assert "repository.add" in actions


def test_project_not_found(client: TestClient, db_session: Session) -> None:
    _login(client, db_session)
    res = client.get("/api/v1/projects/999")
    assert res.status_code == 404


def test_projects_listed_hide_inactive(client: TestClient, db_session: Session) -> None:
    _login(client, db_session)
    created = client.post("/api/v1/projects", json={"name": "To Deactivate"}).json()
    client.patch(f"/api/v1/projects/{created['id']}", json={"is_active": False})

    assert client.get("/api/v1/projects").json()["total"] == 0
    assert client.get("/api/v1/projects?include_inactive=true").json()["total"] == 1
