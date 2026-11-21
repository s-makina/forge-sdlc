"""Workspace provisioning and lifecycle tests for subphase 3.2."""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.deps.container import get_container
from app.docker.client import DockerClient
from app.models.execution import Execution, ExecutionStatus
from app.schemas.execution import ExecutionCreate
from app.services import executions, workspace


class FakeDockerClient(DockerClient):
    """In-memory Docker client recording create/start/stop/remove calls."""

    def __init__(self) -> None:
        self.created: list[str] = []
        self.started: list[str] = []
        self.stopped: list[str] = []
        self.removed: list[str] = []
        self.container_id = "container-123"

    def create_container(self, spec: object) -> str:  # type: ignore[override]
        self.created.append(spec.name)  # type: ignore[attr-defined]
        return self.container_id

    def start_container(self, container_id: str) -> None:
        self.started.append(container_id)

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


def _make_execution(db: Session) -> Execution:
    return executions.create_execution(
        db,
        ExecutionCreate(
            project_id=1,
            repository_url="https://github.com/example/app.git",
            branch="main",
        ),
    )


def test_build_spec_sets_policies(db_session: Session) -> None:
    execution = _make_execution(db_session)
    settings = get_container().settings
    spec = workspace.build_spec(execution, settings)
    assert spec.name == f"forgesdlc-exec-{execution.execution_id}"
    assert spec.image == settings.workspace_image
    assert spec.cpu_limit == settings.workspace_cpu_limit
    assert spec.memory_limit == settings.workspace_memory_limit
    assert spec.working_dir == "/workspace"
    assert spec.environment["EXECUTION_ID"] == execution.execution_id


def test_provision_workspace_moves_to_ready(db_session: Session) -> None:
    execution = _make_execution(db_session)
    docker = FakeDockerClient()
    settings = get_container().settings

    result = workspace.provision_workspace(db_session, execution, docker, settings)

    assert result.status == ExecutionStatus.READY.value
    assert result.container_id == "container-123"
    assert docker.created == [f"forgesdlc-exec-{execution.execution_id}"]
    assert docker.started == ["container-123"]


def test_provision_failure_moves_to_failed(db_session: Session) -> None:
    execution = _make_execution(db_session)

    class BrokenDocker(FakeDockerClient):
        def create_container(self, spec: object) -> str:  # type: ignore[override]
            raise RuntimeError("no daemon")

    result = workspace.provision_workspace(
        db_session, execution, BrokenDocker(), get_container().settings
    )

    assert result.status == ExecutionStatus.FAILED.value
    assert "provision failed" in (result.error_message or "")


def test_cleanup_workspace_stops_and_removes(db_session: Session) -> None:
    execution = _make_execution(db_session)
    docker = FakeDockerClient()
    settings = get_container().settings

    workspace.provision_workspace(db_session, execution, docker, settings)
    result = workspace.cleanup_workspace(db_session, execution, docker)

    assert result.status == ExecutionStatus.DONE.value
    assert docker.stopped == ["container-123"]
    assert docker.removed == ["container-123"]


def test_provision_endpoint(client: TestClient, db_session: Session) -> None:
    created = client.post(
        "/api/v1/executions",
        json={"project_id": 1, "repository_url": "https://github.com/example/app.git"},
    ).json()
    execution_id = created["execution_id"]

    docker = FakeDockerClient()
    get_container().register("docker_client", docker)

    res = client.post(f"/api/v1/executions/{execution_id}/provision")
    assert res.status_code == 200
    assert res.json()["status"] == ExecutionStatus.READY.value
    assert res.json()["container_id"] == "container-123"


def test_cleanup_endpoint_uses_container(client: TestClient, db_session: Session) -> None:
    created = client.post(
        "/api/v1/executions",
        json={"project_id": 1, "repository_url": "https://github.com/example/app.git"},
    ).json()
    execution_id = created["execution_id"]

    docker = FakeDockerClient()
    get_container().register("docker_client", docker)

    client.post(f"/api/v1/executions/{execution_id}/provision")
    res = client.post(f"/api/v1/executions/{execution_id}/cleanup")
    assert res.status_code == 200
    assert res.json()["cleaned"] is True
    assert docker.stopped == ["container-123"]
    assert docker.removed == ["container-123"]