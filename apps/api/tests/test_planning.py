"""Plan-pipeline wiring tests for Phase 5.3 (G2).

A feature request should yield requirements + acceptance criteria, a plan
summary, and an ordered set of ``Task`` records with dependencies — the
decomposition the scheduling layer (4.4) then executes.
"""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import codec, hash_password
from app.models.task import TaskStatus
from app.models.user import User
from app.schemas.workflows import WorkflowCreate, WorkflowTemplateCreate
from app.services import planning, tasks, workflows


def _login(client: TestClient, db: Session, email: str = "plan@example.com") -> User:
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


def _make_workflow(db: Session, **inputs) -> int:
    template = workflows.create_template(
        db,
        WorkflowTemplateCreate(
            slug="feature-development",
            name="Feature Development",
            category="feature",
            stages=[
                {"name": "requirements", "agent_role": "business_analyst"},
                {"name": "architecture", "agent_role": "software_architect", "depends_on": ["requirements"]},
                {"name": "planning", "agent_role": "project_manager", "depends_on": ["architecture"]},
                {"name": "implementation", "agent_role": "software_engineer", "depends_on": ["planning"]},
            ],
        ),
    )
    base = {"title": "Dark mode", "description": "Add a dark theme toggle."}
    base.update(inputs)
    created = workflows.create_workflow(
        db,
        WorkflowCreate(project_id=1, template_id=template.id, name="Dark mode", inputs=base),
    )
    return created.id


def test_feature_request_yields_requirements_and_plan(client: TestClient, db_session: Session) -> None:
    _login(client, db_session)
    workflow_id = _make_workflow(db_session)

    res = client.post(f"/api/v1/workflows/{workflow_id}/plan")
    assert res.status_code == 200
    body = res.json()
    assert body["id"] == workflow_id
    assert body["inputs"]["requirements"]
    assert body["inputs"]["plan_summary"]
    assert len(body["inputs"]["requirements"]) >= 1


def test_plan_creates_tasks_with_dependencies(client: TestClient, db_session: Session) -> None:
    _login(client, db_session)
    workflow_id = _make_workflow(db_session)

    client.post(f"/api/v1/workflows/{workflow_id}/plan")

    planned = workflows.get_workflow(db_session, workflow_id)
    assert planned is not None
    items = tasks.list_tasks(db_session, project_id=planned.project_id)
    planned_tasks = [t for t in items if t.workflow_id == workflow_id]
    assert len(planned_tasks) == 5

    # Each task carries acceptance criteria and an assigned planning role.
    assert all(t.acceptance_criteria for t in planned_tasks)
    assert all(t.assigned_role for t in planned_tasks)

    # Tasks are chained in dependency order: each depends on its predecessor.
    for previous, current in zip(planned_tasks, planned_tasks[1:], strict=False):
        deps = [e.depends_on_id for e in current.dependencies_out]
        assert previous.id in deps


def test_plan_service_records_requirements_on_workflow(db_session: Session) -> None:
    workflow_id = _make_workflow(db_session)
    workflow = workflows.get_workflow(db_session, workflow_id)
    assert workflow is not None

    result = planning.plan_from_feature(db_session, workflow)
    assert result.requirements
    assert result.plan_summary
    assert len(result.tasks) == 5

    refreshed = workflows.get_workflow(db_session, workflow_id)
    assert refreshed is not None
    assert refreshed.inputs["requirements"] == result.requirements
    assert refreshed.inputs["plan_summary"] == result.plan_summary


def test_plan_tasks_start_as_draft(db_session: Session) -> None:
    workflow_id = _make_workflow(db_session)
    workflow = workflows.get_workflow(db_session, workflow_id)
    assert workflow is not None

    result = planning.plan_from_feature(db_session, workflow)
    assert all(t.status == TaskStatus.DRAFT.value for t in result.tasks)
