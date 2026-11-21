"""Cleanup and recovery tests for subphase 3.8."""

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.orm import Session

from app.deps.container import get_container
from app.docker.client import DockerClient
from app.models.execution import Execution, ExecutionStatus
from app.schemas.execution import ExecutionCreate
from app.services import executions, recovery


class FakeDockerClient(DockerClient):
    """In-memory Docker client recording teardown calls."""

    def __init__(self) -> None:
        self.stopped: list[str] = []
        self.removed: list[str] = []

    def create_container(self, spec: object) -> str:  # type: ignore[override]
        return "container-123"

    def start_container(self, container_id: str) -> None:
        pass

    def stop_container(self, container_id: str) -> None:
        self.stopped.append(container_id)

    def remove_container(self, container_id: str) -> None:
        self.removed.append(container_id)

    def container_status(self, container_id: str) -> str:
        return "running"

    def get_container_logs(self, container_id: str) -> str:
        return ""

    def exec_run(self, container_id: str, cmd: list[str]) -> tuple[int, str]:
        return (0, "")


def _make_execution(db: Session, **overrides: object) -> Execution:
    payload: dict[str, object] = {
        "project_id": 1,
        "repository_url": "https://github.com/example/app.git",
        "branch": "main",
    }
    payload.update(overrides)
    return executions.create_execution(db, ExecutionCreate(**payload))  # type: ignore[arg-type]


def test_retry_succeeds_after_transient_failure(db_session: Session) -> None:
    calls = {"count": 0}

    def flaky() -> str:
        calls["count"] += 1
        if calls["count"] < 3:
            raise RuntimeError("transient")
        return "ok"

    result = recovery.retry(flaky, attempts=3, delay_seconds=0)
    assert result == "ok"
    assert calls["count"] == 3


def test_retry_escalates_on_final_failure(db_session: Session) -> None:
    escalated: list[Exception] = []

    def boom() -> None:
        raise ValueError("persistent")

    with pytest.raises(ValueError, match="persistent"):
        recovery.retry(
            boom,
            attempts=2,
            delay_seconds=0,
            on_final_failure=escalated.append,
        )
    assert len(escalated) == 1


def test_cleanup_execution_moves_to_done(db_session: Session) -> None:
    execution = _make_execution(db_session)
    execution.container_id = "container-123"
    db_session.commit()
    docker = FakeDockerClient()

    result = recovery.cleanup_execution(db_session, execution, docker)

    assert result.status == ExecutionStatus.DONE.value
    assert docker.stopped == ["container-123"]
    assert docker.removed == ["container-123"]
    assert result.container_id is None


def test_cleanup_execution_tolerates_docker_failure(db_session: Session) -> None:
    execution = _make_execution(db_session)
    execution.container_id = "container-123"
    db_session.commit()

    class BrokenDocker(FakeDockerClient):
        def remove_container(self, container_id: str) -> None:  # type: ignore[override]
            raise RuntimeError("gone")

    result = recovery.cleanup_execution(db_session, execution, BrokenDocker())
    assert result.status == ExecutionStatus.DONE.value


def test_recover_orphans_cleans_up_stale_running(db_session: Session) -> None:
    execution = _make_execution(db_session)
    execution.status = ExecutionStatus.RUNNING.value
    execution.container_id = "container-123"
    # Long enough in the past that it is overdue.
    execution.started_at = datetime.now(timezone.utc) - timedelta(seconds=7200)
    execution.timeout_seconds = 60
    db_session.commit()
    docker = FakeDockerClient()

    recovered = recovery.recover_orphans(
        db_session, docker, get_container().settings, now_epoch=datetime.now(timezone.utc).timestamp()
    )

    assert len(recovered) == 1
    result = recovered[0]
    # Overdue: failed (timeout) then cleaned to done.
    assert result.status == ExecutionStatus.DONE.value
    assert "timed out" in (result.error_message or "")
    assert docker.removed == ["container-123"]


def test_recover_orphans_ignores_terminal(db_session: Session) -> None:
    _make_execution(db_session, task_id="t1")  # created state, not terminal
    done = _make_execution(db_session, task_id="t2")
    done.status = ExecutionStatus.DONE.value
    db_session.commit()

    recovered = recovery.recover_orphans(
        db_session, FakeDockerClient(), get_container().settings
    )
    # Only the non-terminal (created) execution is swept; the done one is ignored.
    assert len(recovered) == 1