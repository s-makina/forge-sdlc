"""Task assignment and scheduling tests for Phase 4.4/4.5."""

from sqlalchemy.orm import Session

from app.models.agent import Agent, AgentStatus, AgentVersion
from app.models.task import Task, TaskStatus
from app.schemas.tasks import TaskCreate
from app.services import scheduling, tasks


def _add_agent(db: Session, role: str, slug: str) -> int:
    agent = Agent(slug=slug, name=slug, role=role, is_active=True)
    db.add(agent)
    db.flush()
    db.add(
        AgentVersion(
            agent_id=agent.id,
            version="1.0.0",
            status=AgentStatus.ACTIVE.value,
            instructions="do work",
            capabilities=["implementation"],
            model_profile="default",
            quality_gates=[],
        )
    )
    db.commit()
    return agent.id


def _make_task(db: Session, project_id: int = 1, **overrides) -> Task:
    payload: dict = {
        "project_id": project_id,
        "title": "T",
        "task_type": "feature",
    }
    payload.update(overrides)
    task = tasks.create_task(db, TaskCreate(**payload))
    task.status = TaskStatus.READY.value
    db.commit()
    db.refresh(task)
    return task


def test_assign_to_role_sets_agent(db_session: Session) -> None:
    agent_id = _add_agent(db_session, "software_engineer", "dev")
    task = _make_task(db_session, assigned_role="software_engineer")
    assigned = scheduling.assign_to_role(db_session, task, "software_engineer")
    assert assigned.assigned_agent_id == agent_id
    assert assigned.status == TaskStatus.ASSIGNED.value


def test_assign_no_agent_raises(db_session: Session) -> None:
    task = _make_task(db_session, assigned_role="software_engineer")
    try:
        scheduling.assign_to_role(db_session, task, "software_engineer")
    except scheduling.NoSuitableAgent:
        pass
    else:
        raise AssertionError("expected NoSuitableAgent")


def test_schedulable_respects_dependencies(db_session: Session) -> None:
    dep = _make_task(db_session, title="Dep", task_type="feature")
    task = _make_task(db_session, title="Main", task_type="feature")
    tasks.set_dependencies(db_session, task, [dep.id])

    assert scheduling.schedulable(db_session, task) is False
    tasks.transition_status(db_session, dep, "completed")
    assert scheduling.schedulable(db_session, task) is True


def test_schedule_respects_concurrency_limit(db_session: Session) -> None:
    _add_agent(db_session, "software_engineer", "dev")
    # Three independent ready developer tasks.
    for i in range(3):
        _make_task(db_session, title=f"Task {i}", assigned_role="software_engineer")

    started = scheduling.schedule_ready_tasks(db_session, max_developers=2)
    # Only two run concurrently.
    assert len(started) == 2
    running = tasks.list_tasks(db_session, status=TaskStatus.IN_PROGRESS.value)
    assert len(running) == 2


def test_parallel_developers_get_separate_branches(db_session: Session) -> None:
    _add_agent(db_session, "software_engineer", "dev")
    first = _make_task(db_session, title="Task A", assigned_role="software_engineer")
    second = _make_task(db_session, title="Task B", assigned_role="software_engineer")

    started = scheduling.schedule_ready_tasks(db_session, max_developers=2)
    assert len(started) == 2

    branches = {t.target_branch for t in started}
    # Each developer task is allocated its own task/<id> branch (README §11.1).
    assert branches == {f"task/{first.id}", f"task/{second.id}"}
    assert first.target_branch != second.target_branch


def test_parallel_developers_do_not_share_a_branch(db_session: Session) -> None:
    _add_agent(db_session, "software_engineer", "dev")
    for i in range(3):
        _make_task(db_session, title=f"Task {i}", assigned_role="software_engineer")

    started = scheduling.schedule_ready_tasks(db_session, max_developers=2)
    branches = [t.target_branch for t in started]
    assert len(branches) == len(set(branches))


def test_schedule_skips_blocked_dependencies(db_session: Session) -> None:
    _add_agent(db_session, "software_engineer", "dev")
    dep = _make_task(db_session, title="Dep", task_type="feature")
    main = _make_task(db_session, title="Main", task_type="feature")
    tasks.set_dependencies(db_session, main, [dep.id])

    started = scheduling.schedule_ready_tasks(db_session)
    assert main.id not in [t.id for t in started]
