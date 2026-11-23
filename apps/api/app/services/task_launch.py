"""Explicit single-task launch (Phase 3/4 UI wiring).

Sends a ready task to the execution-manager worker over the internal Compose
network, records the returned execution id on the task, and moves
the task to ``in_progress``. Only repositories registered to the task's project
may be used; arbitrary clone URLs are rejected so untrusted input never reaches
the worker (SSRF / credential leakage hardening).
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.models.project import Repository
from app.models.task import Task
from app.schemas.tasks import TaskLaunchRead
from app.services import tasks


class LaunchError(RuntimeError):
    pass


class NotLaunchable(LaunchError):
    pass


class ExecutionManagerUnavailable(LaunchError):
    pass


def _resolve_repository_url(db: Session, task: Task) -> str:
    """Return the repository URL for the task, restricted to its project."""
    # Prefer an explicitly registered repository on the task's project.
    repo_url = (task.repository_url or "").strip()
    if repo_url:
        registered = db.scalars(
            select(Repository).where(
                Repository.project_id == task.project_id,
                Repository.is_active.is_(True),
                Repository.url == repo_url,
            )
        ).first()
        if registered is None:
            raise NotLaunchable(
                "repository is not registered to this project; register it in Projects first"
            )
        return repo_url
    raise NotLaunchable("task has no repository_url")


def launch_task(
    db: Session,
    task: Task,
    *,
    prompt: str,
    http_client: Any | None = None,
    settings: Settings | None = None,
) -> TaskLaunchRead:
    """Create an execution for ``task`` and mark it launched.

    ``http_client`` is an injectable POST helper (``post(url, json, headers)``)
    so the worker call is testable without a live execution-manager.
    """
    settings = settings or get_settings()

    if not tasks.is_launchable(db, task):
        raise NotLaunchable(
            f"task {task.id} is not launchable (must be ready with a repository and satisfied dependencies)"
        )

    repository_url = _resolve_repository_url(db, task)
    if not task.model_profile and task.assigned_role:
        raise NotLaunchable(
            "task has no model profile; assign an active agent/role first"
        )

    payload = {
        "project_id": task.project_id,
        "task_id": str(task.id),
        "repository_url": repository_url,
        "branch": task.target_branch,
        "image": None,
        "cpu_limit": task.cpu_limit,
        "memory_limit": task.memory_limit,
        "disk_limit": task.disk_limit,
        "timeout_seconds": task.timeout_seconds,
        "network_policy": task.network_policy,
    }

    headers = {
        "Content-Type": "application/json",
        "X-ForgeSDLC-Token": settings.execution_manager_token or "forgesdlc-local",
    }
    url = f"{settings.execution_manager_url.rstrip('/')}/executions"
    try:
        if http_client is not None:
            response = http_client.post(url, json=payload, headers=headers)
        else:
            response = _post(url, payload, headers)
    except Exception as exc:  # noqa: BLE001 - network boundary
        raise ExecutionManagerUnavailable(f"execution manager unreachable: {exc}") from None

    status_code = getattr(response, "status_code", None)
    if status_code is None:
        raise ExecutionManagerUnavailable("execution manager returned an invalid response")

    if status_code not in (200, 201):
        detail = getattr(response, "text", None) or getattr(response, "content", None)
        raise LaunchError(f"execution manager rejected request ({status_code}): {detail}")

    data = response.json()
    execution_id = str(data["execution_id"])

    # Only move the task to in_progress once an execution was durably created.
    task.last_execution_id = execution_id
    task.last_execution_status = str(data.get("status", "created"))
    tasks.mark_launched(db, task, result_summary=f"launched execution {execution_id}")

    return TaskLaunchRead(
        task_id=task.id,
        execution_id=execution_id,
        status=task.status,
    )


def _post(url: str, payload: dict[str, object], headers: dict[str, str]) -> Any:
    import httpx

    return httpx.post(url, json=payload, headers=headers, timeout=30.0)
