"""Workspace provisioning and lifecycle (subphase 3.2).

Builds an isolated workspace container per execution with the policy columns
recorded on the execution (README §12.2), and drives the lifecycle:
created -> ready -> running -> succeeded | failed -> cleaning -> done.

Cloning/branching (3.3) and the coding runtime (3.4) are orchestrated by the
higher-level executor; this module owns the container lifecycle primitives.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.docker.client import ContainerSpec, DockerClient
from app.models.execution import Execution, ExecutionStatus
from app.services import executions


def build_spec(execution: Execution, settings: Settings, mounts: list[dict[str, str]] | None = None) -> ContainerSpec:
    """Build the container spec for an execution's workspace."""
    allowlist = [h.strip() for h in settings.workspace_network_allowlist.split(",") if h.strip()]
    return ContainerSpec(
        name=f"forgesdlc-exec-{execution.execution_id}",
        image=execution.image,
        working_dir="/workspace",
        cpu_limit=execution.cpu_limit,
        memory_limit=execution.memory_limit,
        disk_limit=execution.disk_limit,
        network_policy=execution.network_policy,
        network_allowlist=allowlist,
        environment={
            "EXECUTION_ID": execution.execution_id,
            "PROJECT_ID": str(execution.project_id),
            "TASK_ID": execution.task_id or "",
        },
        mounts=mounts or [],
        command=["sleep", "infinity"],
    )


def provision_workspace(
    db: Session,
    execution: Execution,
    docker: DockerClient,
    settings: Settings,
    mounts: list[dict[str, str]] | None = None,
) -> Execution:
    """Create and start the workspace container, moving to ``ready``.

    On failure the execution is moved to ``failed`` with an error message.
    """
    try:
        spec = build_spec(execution, settings, mounts=mounts)
        container_id = docker.create_container(spec)
        docker.start_container(container_id)
        execution.container_id = container_id
    except Exception as exc:  # noqa: BLE001 - surface any provisioning failure
        execution.error_message = f"provision failed: {exc}"
        return executions.transition(db, execution, ExecutionStatus.FAILED)

    return executions.transition(db, execution, ExecutionStatus.READY)


def start_execution(db: Session, execution: Execution) -> Execution:
    """Mark an execution running."""
    return executions.transition(db, execution, ExecutionStatus.RUNNING)


def fail_execution(db: Session, execution: Execution, message: str) -> Execution:
    """Mark an execution failed with an error message."""
    execution.error_message = message
    return executions.transition(db, execution, ExecutionStatus.FAILED)


def succeed_execution(db: Session, execution: Execution) -> Execution:
    """Mark an execution succeeded."""
    return executions.transition(db, execution, ExecutionStatus.SUCCEEDED)


def cleanup_workspace(
    db: Session,
    execution: Execution,
    docker: DockerClient,
) -> Execution:
    """Stop and remove the container, then mark the execution done (3.8)."""
    if execution.container_id:
        try:
            docker.stop_container(execution.container_id)
        except Exception:  # noqa: BLE001 - best-effort cleanup
            pass
        try:
            docker.remove_container(execution.container_id)
        except Exception:  # noqa: BLE001 - best-effort cleanup
            pass
    return executions.transition(db, execution, ExecutionStatus.DONE)