"""Repository cloning and branch management (subphase 3.3).

Clones or updates the project repository into the workspace container and
checks out a task branch named ``task/<execution-id>`` (README §12.2).

Push + PR are deferred to Phase 5; this subphase ensures the workspace starts
on the correct repo state and task branch.
"""

from __future__ import annotations

import shlex

from sqlalchemy.orm import Session

from app.docker.client import DockerClient
from app.models.execution import Execution
from app.services import workspace


def task_branch(execution: Execution) -> str:
    """Return the task branch name for an execution."""
    return f"task/{execution.execution_id}"


def clone_repository(
    docker: DockerClient,
    execution: Execution,
    workspace_dir: str = "/workspace",
) -> tuple[int, str]:
    """Clone the repository and checkout a task branch.

    Runs inside the (already provisioned) workspace container. Returns
    (exit_code, combined_output). A non-zero exit code means cloning failed.
    """
    if not execution.container_id:
        raise RuntimeError("workspace container is not provisioned")

    container_id = execution.container_id
    branch = task_branch(execution)
    repo_url = execution.repository_url
    repo_name = repo_url.rstrip("/").split("/")[-1]
    if repo_name.endswith(".git"):
        repo_name = repo_name[: -len(".git")]

    repo_dir = f"{workspace_dir}/{repo_name}"

    commands = [
        f"git ls-remote --heads origin {branch} || true",
        f"git clone --depth 1 {shlex.quote(repo_url)} {repo_dir} || true",
        f"git -C {repo_dir} fetch origin {shlex.quote(branch)} || true",
        f"git -C {repo_dir} checkout -B {shlex.quote(branch)} origin/{shlex.quote(execution.branch)} || git -C {repo_dir} checkout -B {branch}",
    ]
    outputs: list[str] = []
    exit_code = 0
    for cmd in commands:
        code, out = docker.exec_run(container_id, ["/bin/sh", "-c", cmd])
        outputs.append(out)
        if code != 0:
            exit_code = code
    return exit_code, "\n".join(outputs)


def prepare_repository(
    db: Session,
    docker: DockerClient,
    execution: Execution,
    workspace_dir: str = "/workspace",
) -> Execution:
    """Clone/update the repo onto the task branch.

    Moves the execution to ``running`` on success; on failure, to ``failed``.
    """
    try:
        exit_code, output = clone_repository(docker, execution, workspace_dir)
    except Exception as exc:  # noqa: BLE001 - surface cloning failure
        return workspace.fail_execution(db, execution, f"clone failed: {exc}")

    if exit_code != 0:
        return workspace.fail_execution(db, execution, f"clone exited {exit_code}: {output[-500:]}")

    return workspace.start_execution(db, execution)