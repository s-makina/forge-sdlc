"""Agent registry and definition tests."""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import codec, hash_password
from app.models.user import User
from app.services import seeds


def _login(client: TestClient, db: Session) -> None:
    user = User(
        email="agent-tester@example.com",
        password_hash=hash_password("secret"),
        display_name="Agent Tester",
        is_active=True,
        is_operator=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    client.cookies.set(get_settings().session_cookie_name, codec.create(user.id))


def _seed(db: Session) -> None:
    seeds.seed_registries(db)
    seeds.seed_agents(db)


def test_seed_registers_six_mvp_roles(client: TestClient, db_session: Session) -> None:
    _login(client, db_session)
    _seed(db_session)

    res = client.get("/api/v1/agents")
    assert res.status_code == 200
    slugs = {item["slug"] for item in res.json()["items"]}
    assert slugs == {
        "business-analyst",
        "project-manager",
        "software-architect",
        "developer",
        "qa-engineer",
        "code-reviewer",
    }


def test_create_agent_with_first_version(client: TestClient, db_session: Session) -> None:
    _login(client, db_session)
    _seed(db_session)

    res = client.post(
        "/api/v1/agents",
        json={
            "slug": "manual-role",
            "name": "Manual Role",
            "role": "reviewer",
            "instructions": "Review changes.",
            "capabilities": ["review"],
            "model_profile": "review-specialist",
            "tools": ["repository_read"],
            "skills": ["code-review"],
        },
    )
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["slug"] == "manual-role"
    assert len(body["versions"]) == 1
    assert body["versions"][0]["status"] == "candidate"


def test_unknown_tool_rejected_on_create(client: TestClient, db_session: Session) -> None:
    _login(client, db_session)
    _seed(db_session)

    res = client.post(
        "/api/v1/agents",
        json={
            "slug": "bad-tools",
            "name": "Bad Tools",
            "role": "engineer",
            "instructions": "x",
            "model_profile": "coding-strong",
            "tools": ["does-not-exist"],
        },
    )
    assert res.status_code == 422
    assert "does-not-exist" in res.text


def test_update_creates_new_version_not_overwrite(
    client: TestClient, db_session: Session
) -> None:
    _login(client, db_session)
    _seed(db_session)

    created = client.post(
        "/api/v1/agents",
        json={
            "slug": "versioned",
            "name": "Versioned",
            "role": "engineer",
            "instructions": "v1 instructions",
            "model_profile": "coding-fast",
        },
    ).json()
    agent_id = created["id"]
    assert created["versions"][0]["version"] == "1.0.0"

    res = client.patch(f"/api/v1/agents/{agent_id}", json={"instructions": "v2 instructions"})
    assert res.status_code == 200, res.text
    versions = res.json()["versions"]
    assert len(versions) == 2
    assert versions[0]["instructions"] == "v1 instructions"
    assert versions[1]["instructions"] == "v2 instructions"
    assert versions[1]["version"] == "1.0.1"


def test_promotion_path_draft_candidate_active_retires_previous(
    client: TestClient, db_session: Session
) -> None:
    _login(client, db_session)
    _seed(db_session)

    created = client.post(
        "/api/v1/agents",
        json={
            "slug": "promo",
            "name": "Promo",
            "role": "engineer",
            "instructions": "one",
            "model_profile": "coding-fast",
        },
    ).json()
    agent_id = created["id"]

    v1_id = created["versions"][0]["id"]
    assert created["versions"][0]["status"] == "candidate"

    # candidate -> active (first active)
    res = client.post(f"/api/v1/agents/versions/{v1_id}/action", json={"action": "activate"})
    assert res.status_code == 200
    assert res.json()["status"] == "active"

    # create a second version (candidate)
    res = client.post(
        f"/api/v1/agents/{agent_id}/versions",
        json={"instructions": "two", "model_profile": "coding-fast"},
    )
    assert res.status_code == 201
    v2_id = res.json()["id"]

    # activate v2 -> v1 retires
    res = client.post(f"/api/v1/agents/versions/{v2_id}/action", json={"action": "activate"})
    assert res.status_code == 200
    assert res.json()["status"] == "active"

    agent = client.get(f"/api/v1/agents/{agent_id}").json()
    statuses = {v["version"]: v["status"] for v in agent["versions"]}
    assert statuses["1.0.0"] == "retired"
    assert statuses["1.0.1"] == "active"


def test_import_yaml_definition_and_idempotent_reimport(
    client: TestClient, db_session: Session
) -> None:
    _login(client, db_session)
    _seed(db_session)

    yaml_doc = (
        "agent:\n"
        "  id: import-me\n"
        "  name: Import Me\n"
        "  version: 1.0.0\n"
        "  role: engineer\n"
        "  instructions: imported\n"
        "  model_profile: coding-fast\n"
        "  tools:\n"
        "    - repository_read\n"
        "  skills:\n"
        "    - clean-code\n"
    )
    res = client.post("/api/v1/agents/import", json={"definition": yaml_doc})
    assert res.status_code == 201, res.text
    first = res.json()
    assert first["created_agent"] is True
    assert first["created_version"] is True

    res2 = client.post("/api/v1/agents/import", json={"definition": yaml_doc})
    assert res2.status_code == 201
    second = res2.json()
    assert second["created_agent"] is False
    assert second["created_version"] is False


def test_validate_endpoint_reports_invalid_yaml(client: TestClient, db_session: Session) -> None:
    _login(client, db_session)
    res = client.post(
        "/api/v1/agents/validate",
        json={"definition": "agent:\n  id: broken\n  version: nope\n"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["valid"] is False
    assert any("semantic version" in e["message"] for e in body["errors"])
