"""High-level execution orchestrator (subphases 3.2-3.8).

Coordinates the workspace lifecycle against the Docker client, the repository
cloner (3.3), the OpenHands runtime (3.4), the terminal/test runner (3.5),
policy enforcement incl. timeouts (3.6), log/artefact capture (3.7), and
cleanup/recovery (3.8). Each step is idempotent enough to be driven by the
workflow orchestrator (Phase 4).
"""

from __future__ import annotations

import time

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.docker.client import DockerClient
from app.models.execution import Execution, ExecutionStatus
from app.services import executions, policies, recovery, workspace


def provision(db: Session, execution: Execution, docker: DockerClient, settings: Settings) -> Execution:
    """Provision the workspace container, moving the execution to ``ready``."""
    return workspace.provision_workspace(db, execution, docker, settings)


def run(db: Session, execution: Execution) -> Execution:
    """Mark an execution running (invoked by the runtime/terminal steps)."""
    return workspace.start_execution(db, execution)


def succeed(db: Session, execution: Execution) -> Execution:
    """Mark an execution succeeded."""
    return workspace.succeed_execution(db, execution)


def fail(db: Session, execution: Execution, message: str) -> Execution:
    """Mark an execution failed."""
    return workspace.fail_execution(db, execution, message)


def cleanup(db: Session, execution: Execution, docker: DockerClient) -> Execution:
    """Stop/remove the container, revoke creds, and mark the execution done."""
    return recovery.cleanup_execution(db, execution, docker)


def recover(db: Session, docker: DockerClient, settings: Settings) -> list[Execution]:
    """Recover orphaned executions after a worker/infra failure (3.8)."""
    return recovery.recover_orphans(db, docker, settings)


def observe(db: Session, execution_id: str) -> Execution | None:
    """Return the current execution record for status polling."""
    return executions.get_execution(db, execution_id)


def get_status_value(execution: Execution) -> str:
    """Return the lifecycle status string."""
    return execution.status


def check_timeout(db: Session, execution: Execution) -> Execution:
    """Fail an execution that has exceeded its time budget.

    Returns the execution unchanged if still within budget; otherwise moves it
    to ``failed`` (timeout) so a runaway container is capped (README §12.3).
    """
    if execution.status not in (ExecutionStatus.RUNNING.value, ExecutionStatus.READY.value):
        return execution
    if policies.is_timed_out(execution, time.time()):
        return workspace.fail_execution(db, execution, "execution timed out")
    return execution