"""OpenHands coding-runtime integration (subphase 3.4).

Wires the OpenHands Software Agent SDK as the coding runtime inside the
workspace container and gives the coding agent repository read/write,
terminal, and test-runner tools.

Agent permissions (README §8.4, NFR-1.2) are enforced at this boundary: an
agent without the required permission is refused the tool. Merge and
production-access actions are always denied to coding agents (FR-5.5).
"""

from __future__ import annotations

import abc
from dataclasses import dataclass


@dataclass(frozen=True)
class AgentPermissions:
    """The tool permissions granted to a coding agent (subset of §8.4)."""

    write_repository: bool = False
    run_terminal: bool = True
    run_tests: bool = True
    push_branch: bool = False
    open_pr: bool = False
    access_credentials: bool = False
    production_access: bool = False
    merge: bool = False


@dataclass(frozen=True)
class ToolResult:
    """A structured result from a coding-runtime tool call."""

    ok: bool
    output: str
    exit_code: int = 0
    error: str | None = None


class CodingRuntime(abc.ABC):
    """Coding-runtime surface used by the executor."""

    @abc.abstractmethod
    def start_session(
        self,
        workspace_dir: str,
        permissions: AgentPermissions,
        model_profile: str | None = None,
    ) -> str:
        """Start an OpenHands session bound to a workspace; return a session id."""

    @abc.abstractmethod
    def edit_file(self, session_id: str, path: str, content: str) -> ToolResult:
        """Write/overwrite a file in the repository (requires write_repository)."""

    @abc.abstractmethod
    def run_command(self, session_id: str, command: str) -> ToolResult:
        """Run a shell command in the workspace terminal."""

    @abc.abstractmethod
    def run_tests(self, session_id: str, command: str | None = None) -> ToolResult:
        """Run the project's test command and capture results."""

    @abc.abstractmethod
    def run_task(self, session_id: str, prompt: str) -> ToolResult:
        """Send task instructions and run the coding agent until it stops."""

    @abc.abstractmethod
    def close_session(self, session_id: str) -> None:
        """Tear down an OpenHands session."""


class OpenHandsSdkRuntime(CodingRuntime):
    """Production runtime backed by the OpenHands SDK (lazily resolved)."""

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        model: str | None = None,
    ) -> None:
        self._base_url = base_url or ""
        self._api_key = api_key or ""
        self._model = model or "default"
        self._permissions: dict[str, AgentPermissions] = {}
        self._sessions: dict[str, object] = {}

    def start_session(
        self,
        workspace_dir: str,
        permissions: AgentPermissions,
        model_profile: str | None = None,
    ) -> str:
        from openhands.sdk import LLM, Agent, Conversation, Tool  # type: ignore[import-untyped]
        from openhands.tools.file_editor import FileEditorTool  # type: ignore[import-untyped]
        from openhands.tools.terminal import TerminalTool  # type: ignore[import-untyped]

        model = model_profile or self._model
        llm = LLM(
            model=model,
            api_key=self._api_key or None,
            base_url=self._base_url or None,
        )
        agent = Agent(
            llm=llm,
            tools=[
                Tool(name=TerminalTool.name),
                Tool(name=FileEditorTool.name),
            ],
        )
        conversation = Conversation(agent=agent, workspace=workspace_dir)
        session_id = f"conversation-{len(self._sessions) + 1}"
        self._permissions[session_id] = permissions
        self._sessions[session_id] = conversation
        return session_id

    def _resolve_sdk(self) -> object:
        import openhands  # type: ignore[import-untyped]

        return openhands

    def _check(self, session_id: str, permission: bool, action: str) -> None:
        perms = self._permissions.get(session_id)
        if perms is None:
            raise RuntimeError("no active OpenHands session")
        if not permission:
            raise PermissionError(f"agent lacks permission: {action}")

    def edit_file(self, session_id: str, path: str, content: str) -> ToolResult:
        self._check(session_id, self._permissions[session_id].write_repository, "write_repository")
        try:
            session = self._sessions[session_id]
            result = session.edit_file(path, content)  # type: ignore[attr-defined]
            return _coerce(result)
        except Exception as exc:  # noqa: BLE001
            return ToolResult(ok=False, output="", exit_code=1, error=str(exc))

    def run_command(self, session_id: str, command: str) -> ToolResult:
        self._check(session_id, self._permissions[session_id].run_terminal, "run_terminal")
        try:
            session = self._sessions[session_id]
            result = session.run_command(command)  # type: ignore[attr-defined]
            return _coerce(result)
        except Exception as exc:  # noqa: BLE001
            return ToolResult(ok=False, output="", exit_code=1, error=str(exc))

    def run_tests(self, session_id: str, command: str | None = None) -> ToolResult:
        self._check(session_id, self._permissions[session_id].run_tests, "run_tests")
        try:
            session = self._sessions[session_id]
            result = session.run_tests(command)  # type: ignore[attr-defined]
            return _coerce(result)
        except Exception as exc:  # noqa: BLE001
            return ToolResult(ok=False, output="", exit_code=1, error=str(exc))

    def run_task(self, session_id: str, prompt: str) -> ToolResult:
        self._check(session_id, self._permissions[session_id].write_repository, "write_repository")
        try:
            session = self._sessions[session_id]
            session.send_message(prompt)  # type: ignore[attr-defined]
            result = session.run()  # type: ignore[attr-defined]
            return _coerce(result)
        except Exception as exc:  # noqa: BLE001
            return ToolResult(ok=False, output="", exit_code=1, error=str(exc))

    def close_session(self, session_id: str) -> None:
        session = self._sessions.pop(session_id, None)
        self._permissions.pop(session_id, None)
        if session is not None:
            try:
                session.close()  # type: ignore[attr-defined]
            except Exception:  # noqa: BLE001 - closing a session is best-effort
                pass


def _coerce(result: object) -> ToolResult:
    """Normalise an OpenHands tool result into a ToolResult."""
    if isinstance(result, ToolResult):
        return result
    if isinstance(result, tuple) and len(result) == 2:
        exit_code, output = result
        return ToolResult(ok=int(exit_code) == 0, output=str(output), exit_code=int(exit_code))
    if isinstance(result, str):
        return ToolResult(ok=True, output=result)
    return ToolResult(ok=True, output=str(result))
