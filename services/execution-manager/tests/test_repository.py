"""Repository cloning and branch management tests for subphase 3.3."""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.deps.container import get_container
from app.docker.client import DockerClient
from app.models.execution import Execution, ExecutionStatus
from app.schemas.execution import ExecutionCreate
from app.services import executions, repository, workspace


class RecordingDocker(DockerClient):
    """Records exec_run commands and returns a configurable exit code."""

    def __init__(self, *, exit_code: int = 0) -> None:
        self.exit_code = exit_code
        self.commands: list[list[str]] = []
        self.container_id = "container-1"
        self.started: list[str] = []
        self.removed: list[str] = []

    def create_container(self, spec: object) -> str:  # type: ignore[override]
        return self.container_id

    def start_container(self, container_id: str) -> None:
        self.started.append(container_id)

    def stop_container(self, container_id: str) -> None:
        pass

    def remove_container(self, container_id: str) -> None:
        self.removed.append(container_id)

    def container_status(self, container_id: str) -> str:
        return "running"

    def get_container_logs(self, container_id: str) -> str:
        return ""

    def exec_run(self, container_id: str, cmd: list[str]) -> tuple[int, str]:
        self.commands.append(cmd)
        return (self.exit_code, "ok")


def _execution_with_container(db: Session) -> tuple[Execution, RecordingDocker]:
    execution = executions.create_execution(
        db,
        ExecutionCreate(
            project_id=1,
            repository_url="https://github.com/example/app.git",
            branch="main",
        ),
    )
    docker = RecordingDocker()
    workspace.provision_workspace(db, execution, docker, get_settings())
    return execution, docker


def test_task_branch_name(db_session: Session) -> None:
    execution = executions.create_execution(
        db_session,
        ExecutionCreate(project_id=1, repository_url="https://github.com/example/app.git"),
    )
    assert repository.task_branch(execution) == f"task/{execution.execution_id}"


def test_clone_repository_runs_inside_container(db_session: Session) -> None:
    execution, docker = _execution_with_container(db_session)

    exit_code, _ = repository.clone_repository(docker, execution)

    assert exit_code == 0
    # At least one command ran with /bin/sh -c.
    assert any(cmd[0] == "/bin/sh" for cmd in docker.commands)
    # A clone command targeting the repo dir was issued.
    assert any("clone" in cmd[1] for cmd in docker.commands)


def test_prepare_repository_moves_to_running(db_session: Session) -> None:
    execution, docker = _execution_with_container(db_session)

    result = repository.prepare_repository(db_session, docker, execution)

    assert result.status == ExecutionStatus.RUNNING.value


def test_prepare_repository_fails_on_nonzero_exit(db_session: Session) -> None:
    execution, docker = _execution_with_container(db_session)
    docker.exit_code = 128

    result = repository.prepare_repository(db_session, docker, execution)

    assert result.status == ExecutionStatus.FAILED.value
    assert "clone exited" in (result.error_message or "")


def test_prepare_repository_fails_without_container(db_session: Session) -> None:
    execution = executions.create_execution(
        db_session,
        ExecutionCreate(project_id=1, repository_url="https://github.com/example/app.git"),
    )
    docker = RecordingDocker()

    result = repository.prepare_repository(db_session, docker, execution)

    assert result.status == ExecutionStatus.FAILED.value
    assert "clone failed" in (result.error_message or "")


def test_prepare_endpoint(client: TestClient, db_session: Session) -> None:
    created = client.post(
        "/api/v1/executions",
        json={"project_id": 1, "repository_url": "https://github.com/example/app.git"},
    ).json()
    execution_id = created["execution_id"]

    docker = RecordingDocker()
    get_container().register("docker_client", docker)
    client.post(f"/api/v1/executions/{execution_id}/provision")

    res = client.post(f"/api/v1/executions/{execution_id}/prepare")
    assert res.status_code == 200
    assert res.json()["status"] == ExecutionStatus.RUNNING.value