"""Terminal and test execution tests for subphase 3.5."""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.adapters.registry import Adapter, detect, get_adapter
from app.core.config import get_settings
from app.deps.container import get_container
from app.docker.client import DockerClient
from app.models.execution import Execution, ExecutionStatus
from app.schemas.execution import ExecutionCreate
from app.services import executions, terminal, workspace


class ScriptedDocker(DockerClient):
    """Docker client returning a scripted exit code per exec_run."""

    def __init__(self, *, exit_code: int = 0) -> None:
        self.exit_code = exit_code
        self.commands: list[str] = []
        self.container_id = "container-1"

    def create_container(self, spec: object) -> str:  # type: ignore[override]
        return self.container_id

    def start_container(self, container_id: str) -> None:
        pass

    def stop_container(self, container_id: str) -> None:
        pass

    def remove_container(self, container_id: str) -> None:
        pass

    def container_status(self, container_id: str) -> str:
        return "running"

    def get_container_logs(self, container_id: str) -> str:
        return ""

    def exec_run(self, container_id: str, cmd: list[str]) -> tuple[int, str]:
        self.commands.append(cmd[1])
        return (self.exit_code, "output" if self.exit_code == 0 else "boom")


def _provisioned_execution(db: Session) -> Execution:
    execution = executions.create_execution(
        db,
        ExecutionCreate(
            project_id=1,
            repository_url="https://github.com/example/app.git",
            branch="main",
            adapter_name="python",
        ),
    )
    docker = ScriptedDocker()
    workspace.provision_workspace(db, execution, docker, get_settings())
    return execution


def test_detect_python() -> None:
    adapter = detect(["pyproject.toml"])
    assert adapter.name == "python"
    assert "pytest" in adapter.test[0]


def test_detect_nextjs() -> None:
    adapter = detect(["package.json", "next.config.js"])
    assert adapter.name == "nextjs"
    assert "pnpm test" in adapter.test


def test_get_adapter_by_name() -> None:
    assert get_adapter("spring-boot").name == "spring-boot"
    assert get_adapter("missing").name == "python"  # default


def test_run_phase_uses_adapter_commands(db_session: Session) -> None:
    execution = _provisioned_execution(db_session)
    docker = ScriptedDocker()
    adapter = get_adapter("python")

    results = terminal.run_phase(db_session, docker, execution, adapter, "test")

    assert len(results) == 1
    assert results[0].succeeded is True
    assert results[0].command == "python -m pytest"


def test_run_tests_success_keeps_running(db_session: Session) -> None:
    execution = _provisioned_execution(db_session)
    docker = ScriptedDocker()

    results, result_execution = terminal.run_tests(db_session, docker, execution)

    assert results[0].succeeded is True
    assert result_execution.status == ExecutionStatus.RUNNING.value


def test_run_tests_failure_moves_to_failed(db_session: Session) -> None:
    execution = _provisioned_execution(db_session)
    docker = ScriptedDocker(exit_code=1)

    results, result_execution = terminal.run_tests(db_session, docker, execution)

    assert results[0].succeeded is False
    assert result_execution.status == ExecutionStatus.FAILED.value
    assert "tests failed" in (result_execution.error_message or "")


def test_test_endpoint(client: TestClient, db_session: Session) -> None:
    created = client.post(
        "/api/v1/executions",
        json={
            "project_id": 1,
            "repository_url": "https://github.com/example/app.git",
            "adapter_name": "python",
        },
    ).json()
    execution_id = created["execution_id"]

    docker = ScriptedDocker()
    get_container().register("docker_client", docker)
    client.post(f"/api/v1/executions/{execution_id}/provision")

    res = client.post(f"/api/v1/executions/{execution_id}/test")
    assert res.status_code == 200
    assert res.json()["status"] == ExecutionStatus.RUNNING.value