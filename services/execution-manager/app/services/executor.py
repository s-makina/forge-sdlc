"""High-level execution orchestrator (subphases 3.2-3.5).

Coordinates the workspace lifecycle against the Docker client, the repository
cloner (3.3) and, later, the OpenHands runtime (3.4) and terminal/test runner
(3.5). Each step is idempotent enough to be driven by the workflow orchestrator
(Phase 4).
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.docker.client import DockerClient
from app.models.execution import Execution
from app.services import executions, workspace


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
    """Stop/remove the container and mark the execution done."""
    return workspace.cleanup_workspace(db, execution, docker)


def observe(db: Session, execution_id: str) -> Execution | None:
    """Return the current execution record for status polling."""
    return executions.get_execution(db, execution_id)


def get_status_value(execution: Execution) -> str:
    """Return the lifecycle status string."""
    return execution.status