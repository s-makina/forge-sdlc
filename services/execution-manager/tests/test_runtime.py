"""OpenHands runtime integration tests for subphase 3.4."""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.deps.container import get_container
from app.models.execution import Execution, ExecutionStatus
from app.openhands.client import AgentPermissions, CodingRuntime, ToolResult
from app.schemas.execution import ExecutionCreate
from app.services import executions, runtime


class FakeRuntime(CodingRuntime):
    """In-memory coding runtime recording calls."""

    def __init__(self, *, fail_start: bool = False) -> None:
        self.fail_start = fail_start
        self.sessions: set[str] = set()
        self.next_session_id = "session-1"
        self.calls: list[str] = []
        self.permissions: dict[str, AgentPermissions] = {}

    def start_session(
        self, workspace_dir: str, permissions: AgentPermissions, model_profile: str | None = None
    ) -> str:
        self.calls.append("start_session")
        if self.fail_start:
            raise RuntimeError("openhands unavailable")
        session_id = self.next_session_id
        self.sessions.add(session_id)
        self.permissions[session_id] = permissions
        return session_id

    def edit_file(self, session_id: str, path: str, content: str) -> ToolResult:
        self.calls.append(f"edit:{path}")
        perms = self.permissions.get(session_id)
        if perms is None or not perms.write_repository:
            return ToolResult(ok=False, output="", exit_code=1, error="no permission")
        return ToolResult(ok=True, output="wrote")

    def run_command(self, session_id: str, command: str) -> ToolResult:
        self.calls.append(f"cmd:{command}")
        return ToolResult(ok=True, output="ok")

    def run_tests(self, session_id: str, command: str | None = None) -> ToolResult:
        self.calls.append("tests")
        return ToolResult(ok=True, output="passed")

    def run_task(self, session_id: str, prompt: str) -> ToolResult:
        self.calls.append(f"task:{prompt}")
        return ToolResult(ok=True, output="task completed")

    def close_session(self, session_id: str) -> None:
        self.calls.append("close")
        self.sessions.discard(session_id)


def _execution(db: Session) -> Execution:
    return executions.create_execution(
        db,
        ExecutionCreate(project_id=1, repository_url="https://github.com/example/app.git"),
    )


def test_default_permissions_are_least_privilege() -> None:
    perms = runtime.default_permissions()
    assert perms.write_repository is True
    assert perms.merge is False
    assert perms.production_access is False
    assert perms.push_branch is False


def test_start_coding_session_moves_to_running(db_session: Session) -> None:
    execution = _execution(db_session)
    fake = FakeRuntime()

    session_id, result = runtime.start_coding_session(db_session, fake, execution)

    assert session_id == "session-1"
    assert result.status == ExecutionStatus.RUNNING.value
    assert result.session_id == "session-1"  # type: ignore[attr-defined]


def test_start_coding_session_failure(db_session: Session) -> None:
    execution = _execution(db_session)
    fake = FakeRuntime(fail_start=True)

    session_id, result = runtime.start_coding_session(db_session, fake, execution)

    assert session_id == ""
    assert result.status == ExecutionStatus.FAILED.value
    assert "runtime start failed" in (result.error_message or "")


def test_edit_file_enforces_write_repository(db_session: Session) -> None:
    execution = _execution(db_session)
    fake = FakeRuntime()
    session_id, _ = runtime.start_coding_session(db_session, fake, execution)

    result = runtime.edit_file(fake, session_id, "src/a.py", "print(1)")

    assert result.ok is True
    assert "edit:src/a.py" in fake.calls


def test_edit_file_denied_without_permission(db_session: Session) -> None:
    execution = _execution(db_session)
    fake = FakeRuntime()
    session_id, _ = runtime.start_coding_session(
        db_session, fake, execution, AgentPermissions(write_repository=False)
    )

    result = runtime.edit_file(fake, session_id, "src/a.py", "x")

    assert result.ok is False
    assert "no permission" in (result.error or "")


def test_run_command_and_tests(db_session: Session) -> None:
    execution = _execution(db_session)
    fake = FakeRuntime()
    session_id, _ = runtime.start_coding_session(db_session, fake, execution)

    cmd = runtime.run_command(fake, session_id, "pnpm test")
    tests = runtime.run_tests(fake, session_id)

    assert cmd.ok is True
    assert tests.ok is True
    assert "cmd:pnpm test" in fake.calls
    assert "tests" in fake.calls


def test_run_task_sends_prompt_to_coding_runtime(db_session: Session) -> None:
    execution = _execution(db_session)
    fake = FakeRuntime()
    session_id, _ = runtime.start_coding_session(db_session, fake, execution)

    result = runtime.run_task(fake, session_id, "Update the README with setup steps")

    assert result.ok is True
    assert result.output == "task completed"
    assert "task:Update the README with setup steps" in fake.calls


def test_close_session_tears_down(db_session: Session) -> None:
    execution = _execution(db_session)
    fake = FakeRuntime()
    session_id, _ = runtime.start_coding_session(db_session, fake, execution)

    runtime.close_session(fake, session_id)

    assert session_id not in fake.sessions


def test_start_session_endpoint(client: TestClient, db_session: Session) -> None:
    created = client.post(
        "/api/v1/executions",
        json={"project_id": 1, "repository_url": "https://github.com/example/app.git"},
    ).json()
    execution_id = created["execution_id"]

    fake = FakeRuntime()
    get_container().register("coding_runtime", fake)

    res = client.post(f"/api/v1/executions/{execution_id}/start-session")
    assert res.status_code == 200
    assert res.json()["status"] == ExecutionStatus.RUNNING.value
    assert res.json()["session_id"] == "session-1"


def test_run_task_endpoint_uses_coding_runtime(client: TestClient, db_session: Session) -> None:
    created = client.post(
        "/api/v1/executions",
        json={"project_id": 1, "repository_url": "https://github.com/example/app.git"},
    ).json()
    execution_id = created["execution_id"]

    fake = FakeRuntime()
    get_container().register("coding_runtime", fake)
    client.post(f"/api/v1/executions/{execution_id}/start-session")

    res = client.post(
        f"/api/v1/executions/{execution_id}/run",
        json={"prompt": "Update the README with setup steps"},
    )
    assert res.status_code == 200
    assert res.json()["ok"] is True
    assert res.json()["output"] == "task completed"
    assert "task:Update the README with setup steps" in fake.calls


def test_run_task_endpoint_failure_moves_to_failed(client: TestClient, db_session: Session) -> None:
    created = client.post(
        "/api/v1/executions",
        json={"project_id": 1, "repository_url": "https://github.com/example/app.git"},
    ).json()
    execution_id = created["execution_id"]

    class BrokenRuntime(FakeRuntime):
        def run_task(self, session_id: str, prompt: str) -> ToolResult:
            return ToolResult(ok=False, output="", exit_code=1, error="agent failed")

    get_container().register("coding_runtime", BrokenRuntime())
    client.post(f"/api/v1/executions/{execution_id}/start-session")

    res = client.post(
        f"/api/v1/executions/{execution_id}/run",
        json={"prompt": "Update the README"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["ok"] is False
    assert "agent failed" in body["error"]
    status = client.get(f"/api/v1/executions/{execution_id}/status").json()
    assert status["status"] == ExecutionStatus.FAILED.value
