"""Coding-runtime orchestration (subphase 3.4).

Binds an OpenHands coding session to an execution workspace and enforces the
agent's permissions (no merge, no production access). The runtime itself is
injected so tests can substitute a fake without a live OpenHands server.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.execution import Execution
from app.openhands.client import AgentPermissions, CodingRuntime, ToolResult
from app.services import workspace


def default_permissions() -> AgentPermissions:
    """Permissions for a developer coding agent (least privilege)."""
    return AgentPermissions(
        write_repository=True,
        run_terminal=True,
        run_tests=True,
        push_branch=False,
        open_pr=False,
        access_credentials=False,
        production_access=False,
        merge=False,
    )


def start_coding_session(
    db: Session,
    runtime: CodingRuntime,
    execution: Execution,
    permissions: AgentPermissions | None = None,
    model_profile: str | None = None,
    workspace_dir: str = "/workspace",
) -> tuple[str, Execution]:
    """Start an OpenHands session for the execution's workspace.

    Returns (session_id, execution). On failure the execution is moved to
    ``failed``.
    """
    perms = permissions or default_permissions()
    try:
        session_id = runtime.start_session(workspace_dir, perms, model_profile)
    except Exception as exc:  # noqa: BLE001 - surface runtime start failure
        return "", workspace.fail_execution(db, execution, f"runtime start failed: {exc}")
    execution.session_id = session_id
    db.commit()
    return session_id, workspace.start_execution(db, execution)


def edit_file(
    runtime: CodingRuntime,
    session_id: str,
    path: str,
    content: str,
) -> ToolResult:
    """Edit a file via the runtime, enforcing write_repository."""
    return runtime.edit_file(session_id, path, content)


def run_command(
    runtime: CodingRuntime,
    session_id: str,
    command: str,
) -> ToolResult:
    """Run a terminal command in the workspace."""
    return runtime.run_command(session_id, command)


def run_tests(
    runtime: CodingRuntime,
    session_id: str,
    command: str | None = None,
) -> ToolResult:
    """Run the project's test command (delegated to Phase 3.5 adapter)."""
    return runtime.run_tests(session_id, command)


def run_task(
    runtime: CodingRuntime,
    session_id: str,
    prompt: str,
) -> ToolResult:
    """Run a task prompt through the coding agent."""
    return runtime.run_task(session_id, prompt)


def close_session(
    runtime: CodingRuntime,
    session_id: str,
) -> None:
    """Tear down an OpenHands session."""
    runtime.close_session(session_id)
