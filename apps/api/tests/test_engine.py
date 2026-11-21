"""Workflow engine tests for Phase 4.6: retry, timeout, cancellation, recovery."""

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.orm import Session

from app.models.workflow_instance import Workflow, WorkflowStatus
from app.schemas.workflows import WorkflowCreate, WorkflowTemplateCreate
from app.services import engine, workflows


def _make_template(db: Session, slug: str = "feature-development") -> int:
    payload = WorkflowTemplateCreate(
        slug=slug,
        name="Feature Development",
        category="feature",
        stages=[
            {"name": "planning", "agent_role": "software_architect"},
            {"name": "implementation", "agent_role": "software_engineer", "depends_on": ["planning"]},
        ],
    )
    return workflows.create_template(db, payload).id


def _make_workflow(db: Session, template_id: int) -> Workflow:
    created = workflows.create_workflow(
        db,
        WorkflowCreate(project_id=1, template_id=template_id, name="Sprint"),
    )
    assert created is not None
    return workflows.get_workflow(db, created.id)  # type: ignore[return-value]


def test_retry_succeeds_after_transient_failures() -> None:
    attempts = 0

    def flaky() -> str:
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise RuntimeError("transient")
        return "ok"

    result = engine.retry(flaky, max_retries=3, base_delay=0)
    assert result == "ok"
    assert attempts == 3


def test_retry_fails_after_max_and_escalates() -> None:
    escalations: list[str] = []

    def always_fails() -> None:
        raise ValueError("boom")

    with pytest.raises(ValueError):
        engine.retry(
            always_fails,
            max_retries=3,
            base_delay=0,
            on_final_failure=lambda exc: escalations.append(str(exc)),
        )
    assert escalations == ["boom"]


def test_advance_workflow_times_out(db_session: Session) -> None:
    template_id = _make_template(db_session, slug="feature-development")
    workflow = _make_workflow(db_session, template_id)
    workflow = workflows.transition_workflow(db_session, workflow, WorkflowStatus.RUNNING.value)
    # Age the workflow past any time budget.
    workflow.started_at = datetime.now(timezone.utc) - timedelta(seconds=4000)
    db_session.commit()

    with pytest.raises(engine.WorkflowTimedOut):
        engine.advance_workflow(db_session, workflow, timeout_seconds=3600)

    db_session.refresh(workflow)
    assert workflow.status == WorkflowStatus.FAILED.value


def test_advance_workflow_succeeds_when_no_runnable_stages(db_session: Session) -> None:
    template_id = _make_template(db_session, slug="feature-development")
    workflow = _make_workflow(db_session, template_id)
    # All stages already terminal -> workflow completes.
    for stage in workflow.stages:
        stage.status = "succeeded"
    db_session.commit()

    result = engine.advance_workflow(db_session, workflow, timeout_seconds=3600)
    assert result.status == WorkflowStatus.SUCCEEDED.value


def test_cancel_workflow_propagates_to_stages(db_session: Session) -> None:
    template_id = _make_template(db_session, slug="feature-development")
    workflow = _make_workflow(db_session, template_id)
    workflow.stages[0].status = "running"
    workflow.stages[1].status = "pending"
    db_session.commit()

    engine.cancel_workflow(db_session, workflow)
    db_session.refresh(workflow)
    assert workflow.status == WorkflowStatus.CANCELLED.value
    assert all(s.status == "cancelled" for s in workflow.stages)


def test_recover_interrupted_parks_pending(db_session: Session) -> None:
    template_id = _make_template(db_session, slug="feature-development")
    workflow = _make_workflow(db_session, template_id)
    workflow.status = WorkflowStatus.RUNNING.value
    # No stage is mid-running -> park back to pending.
    db_session.commit()

    result = engine.recover_interrupted(db_session, workflow)
    assert result.status == WorkflowStatus.PENDING.value


def test_recover_interrupted_fails_mid_running(db_session: Session) -> None:
    template_id = _make_template(db_session, slug="feature-development")
    workflow = _make_workflow(db_session, template_id)
    workflow.status = WorkflowStatus.RUNNING.value
    workflow.stages[0].status = "running"
    db_session.commit()

    result = engine.recover_interrupted(db_session, workflow)
    assert result.status == WorkflowStatus.FAILED.value
    assert workflow.stages[0].status == "failed"