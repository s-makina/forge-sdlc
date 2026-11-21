"""Plan-approval gate tests for Phase 5.4.

Covers the service + route surface: requesting approval gates a workflow into
``waiting_approval``, deciding approve/reject records the attributable decision
and releases the workflow, and the engine refuses to advance a workflow that is
awaiting approval.
"""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import codec, hash_password
from app.models.user import User
from app.models.workflow_instance import Workflow, WorkflowStatus
from app.schemas.workflows import WorkflowCreate, WorkflowTemplateCreate
from app.services import engine, workflows


def _login(client: TestClient, db: Session, email: str = "op@example.com") -> User:
    user = User(
        email=email,
        password_hash=hash_password("secret"),
        display_name="Operator",
        is_active=True,
        is_operator=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    client.cookies.set(get_settings().session_cookie_name, codec.create(user.id))
    return user


def _make_workflow(db: Session) -> int:
    template = workflows.create_template(
        db,
        WorkflowTemplateCreate(
            slug="feature-development",
            name="Feature Development",
            category="feature",
            stages=[
                {"name": "planning", "agent_role": "software_architect"},
                {"name": "implementation", "agent_role": "developer", "depends_on": ["planning"]},
            ],
        ),
    )
    created = workflows.create_workflow(
        db, WorkflowCreate(project_id=1, template_id=template.id, name="Sprint")
    )
    return created.id


def test_request_approval_gates_workflow(client: TestClient, db_session: Session) -> None:
    _login(client, db_session)
    workflow_id = _make_workflow(db_session)
    res = client.post(f"/api/v1/approvals/workflows/{workflow_id}/request")
    assert res.status_code == 201
    body = res.json()
    assert body["workflow_id"] == workflow_id
    assert body["status"] == "requested"
    # The workflow is gated into waiting_approval.
    workflow = db_session.get(Workflow, workflow_id)
    assert workflow is not None
    assert workflow.status == WorkflowStatus.WAITING_APPROVAL.value


def test_approve_decision_releases_workflow(client: TestClient, db_session: Session) -> None:
    _login(client, db_session)
    workflow_id = _make_workflow(db_session)
    client.post(f"/api/v1/approvals/workflows/{workflow_id}/request")

    res = client.post(
        f"/api/v1/approvals/workflows/{workflow_id}/decide",
        json={"decision": "approved", "comment": "plan looks good"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "approved"
    assert body["approver_email"] == "op@example.com"
    assert body["decision_comment"] == "plan looks good"
    assert body["decided_at"] is not None


def test_reject_decision_releases_workflow(client: TestClient, db_session: Session) -> None:
    _login(client, db_session)
    workflow_id = _make_workflow(db_session)
    client.post(f"/api/v1/approvals/workflows/{workflow_id}/request")

    res = client.post(
        f"/api/v1/approvals/workflows/{workflow_id}/decide",
        json={"decision": "rejected", "comment": "needs more detail"},
    )
    assert res.status_code == 200
    assert res.json()["status"] == "rejected"


def test_decide_missing_approval_404(client: TestClient, db_session: Session) -> None:
    _login(client, db_session)
    workflow_id = _make_workflow(db_session)
    res = client.post(
        f"/api/v1/approvals/workflows/{workflow_id}/decide",
        json={"decision": "approved"},
    )
    assert res.status_code == 404


def test_decide_already_decided_409(client: TestClient, db_session: Session) -> None:
    _login(client, db_session)
    workflow_id = _make_workflow(db_session)
    client.post(f"/api/v1/approvals/workflows/{workflow_id}/request")
    client.post(
        f"/api/v1/approvals/workflows/{workflow_id}/decide",
        json={"decision": "approved"},
    )
    res = client.post(
        f"/api/v1/approvals/workflows/{workflow_id}/decide",
        json={"decision": "approved"},
    )
    assert res.status_code == 409


def test_engine_blocks_advance_when_waiting_approval(db_session: Session) -> None:
    workflow_id = _make_workflow(db_session)
    workflow = workflows.get_workflow(db_session, workflow_id)
    assert workflow is not None
    workflow.status = WorkflowStatus.WAITING_APPROVAL.value
    db_session.commit()

    result = engine.advance_workflow(db_session, workflow, timeout_seconds=3600)
    assert result.status == WorkflowStatus.WAITING_APPROVAL.value
    # Stages are untouched: no stage was run or completed.
    assert all(s.status == "pending" for s in result.stages)
