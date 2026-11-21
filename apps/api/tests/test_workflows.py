"""Workflow template and instance tests for Phase 4.2/4.7."""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import codec, hash_password
from app.models.user import User
from app.schemas.workflows import WorkflowTemplateCreate
from app.services import workflows


def _login(client: TestClient, db: Session, email: str = "wf@example.com") -> User:
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


def _make_template(db: Session, **overrides) -> int:
    payload = WorkflowTemplateCreate(
        slug="feature-development",
        name="Feature Development",
        category="feature",
        stages=[
            {"name": "planning", "agent_role": "software_architect"},
            {"name": "implementation", "agent_role": "developer", "depends_on": ["planning"]},
            {"name": "testing", "agent_role": "tester", "depends_on": ["implementation"]},
        ],
    )
    template = workflows.create_template(db, payload)
    return template.id


def test_create_and_get_template(client: TestClient, db_session: Session) -> None:
    _login(client, db_session)
    res = client.post(
        "/api/v1/workflows/templates",
        json={
            "slug": "bug-fix",
            "name": "Bug Fix",
            "category": "bugfix",
            "stages": [{"name": "triage", "agent_role": "developer"}],
        },
    )
    assert res.status_code == 201
    body = res.json()
    assert body["slug"] == "bug-fix"
    assert len(body["stages"]) == 1


def test_duplicate_template_slug_conflict(client: TestClient, db_session: Session) -> None:
    _login(client, db_session)
    template_id = _make_template(db_session)
    assert template_id > 0
    res = client.post(
        "/api/v1/workflows/templates",
        json={
            "slug": "feature-development",
            "name": "Feature Development",
            "category": "feature",
        },
    )
    assert res.status_code == 409


def test_create_workflow_from_template(client: TestClient, db_session: Session) -> None:
    _login(client, db_session)
    template_id = _make_template(db_session)
    res = client.post(
        "/api/v1/workflows",
        json={"project_id": 1, "template_id": template_id, "name": "Sprint 1"},
    )
    assert res.status_code == 201
    body = res.json()
    assert body["status"] == "pending"
    # Stage runs are materialised from the template.
    assert [s["name"] for s in body["stages"]] == ["planning", "implementation", "testing"]


def test_workflow_stage_transitions(client: TestClient, db_session: Session) -> None:
    _login(client, db_session)
    template_id = _make_template(db_session)
    created = client.post(
        "/api/v1/workflows",
        json={"project_id": 1, "template_id": template_id, "name": "Sprint 2"},
    ).json()
    workflow_id = created["id"]

    res = client.post(
        f"/api/v1/workflows/{workflow_id}/stages/0/status", json={"status": "succeeded"}
    )
    assert res.status_code == 200
    assert res.json()["stages"][0]["status"] == "succeeded"


def test_workflow_status_transition(client: TestClient, db_session: Session) -> None:
    _login(client, db_session)
    template_id = _make_template(db_session)
    created = client.post(
        "/api/v1/workflows",
        json={"project_id": 1, "template_id": template_id, "name": "Sprint 3"},
    ).json()
    res = client.post(
        f"/api/v1/workflows/{created['id']}/status", json={"status": "succeeded"}
    )
    assert res.status_code == 200
    assert res.json()["status"] == "succeeded"


def test_seed_default_templates_idempotent(db_session: Session) -> None:
    first = workflows.seed_default_templates(db_session)
    second = workflows.seed_default_templates(db_session)
    assert first >= 1
    assert second == 0


def test_workflow_create_missing_template_404(client: TestClient, db_session: Session) -> None:
    _login(client, db_session)
    res = client.post(
        "/api/v1/workflows",
        json={"project_id": 1, "template_id": 9999, "name": "Ghost"},
    )
    assert res.status_code == 404