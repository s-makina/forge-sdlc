"""Execution routes (Phase 4.4/4.6).

Proxy execution status to the workers that own it:

* pipeline status → execution-manager ``GET /executions/{id}/status``
* durable (Temporal) status → orchestrator ``GET /executions/{id}/run-status``

The control-plane API does not store executions itself; executions are created
when a task is launched and recorded on the task (``last_execution_id`` /
``last_execution_status``). The list endpoint therefore derives executions from
tasks, while the status endpoints reach the owning worker over the internal
network and degrade gracefully (status ``unknown``) when a worker is unreachable.

An injectable HTTP client (``get(url, headers)``) may be registered in the DI
container under ``execution_manager_client`` / ``orchestrator_client`` for
tests; otherwise a raw ``httpx`` request is used, mirroring
``app.services.task_launch``.
"""

from __future__ import annotations

from typing import Any

import httpx
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.container import get_container
from app.db.session import get_db
from app.deps.auth import require_user
from app.models.user import User
from app.schemas.executions import (
    ExecutionList,
    ExecutionStatus,
    ExecutionRunStatus,
    ExecutionSummary,
)
from app.services import tasks

router = APIRouter(prefix="/executions", tags=["executions"])

_TIMEOUT_SECONDS = 8.0


def _headers(token_setting: str) -> dict[str, str]:
    settings = get_settings()
    return {
        "Content-Type": "application/json",
        "X-ForgeSDLC-Token": getattr(settings, token_setting) or "forgesdlc-local",
    }


def _resolve_client(name: str) -> Any | None:
    try:
        return get_container().resolve(name)
    except KeyError:
        return None


def _get_json(url: str, headers: dict[str, str], client_name: str) -> Any | None:
    """GET ``url`` and return its JSON body, or ``None`` on any failure.

    Uses an injectable container client when registered (tests), falling back
    to raw ``httpx`` in production. Any failure degrades to ``None`` so the
    caller can report status ``unknown`` rather than erroring.
    """
    client = _resolve_client(client_name)
    if client is not None and hasattr(client, "get"):
        try:
            response = client.get(url, headers=headers)
            if getattr(response, "status_code", None) != 200:
                return None
            return response.json()
        except Exception:  # noqa: BLE001 - network boundary, degrade to unknown
            return None
    try:
        response = httpx.get(url, headers=headers, timeout=_TIMEOUT_SECONDS)
        if response.status_code != 200:
            return None
        return response.json()
    except Exception:  # noqa: BLE001 - network boundary, degrade to unknown
        return None


@router.get("", response_model=ExecutionList)
def list_executions(
    db: Session = Depends(get_db), _: User = Depends(require_user)
) -> ExecutionList:
    """List executions derived from tasks that have been launched.

    Each item reflects the last known pipeline status recorded on the task
    (a snapshot at launch time); poll the per-execution status endpoints for
    live values.
    """
    items = tasks.list_tasks(db)
    executions: list[ExecutionSummary] = []
    for task in items:
        if task.last_execution_id:
            executions.append(
                ExecutionSummary(
                    execution_id=task.last_execution_id,
                    task_id=task.id,
                    task_title=task.title,
                    status=task.last_execution_status or "created",
                )
            )
    return ExecutionList(items=executions, total=len(executions))


@router.get("/{execution_id}/status", response_model=ExecutionStatus)
def execution_status(
    execution_id: str, _: User = Depends(require_user)
) -> ExecutionStatus:
    """Live execution-manager pipeline status for ``execution_id``."""
    settings = get_settings()
    url = f"{settings.execution_manager_url.rstrip('/')}/executions/{execution_id}/status"
    data = _get_json(
        url, _headers("execution_manager_token"), "execution_manager_client"
    )
    status_value = "unknown"
    if isinstance(data, dict):
        status_value = str(data.get("status", "unknown"))
    return ExecutionStatus(execution_id=execution_id, status=status_value)


@router.get("/{execution_id}/run-status", response_model=ExecutionRunStatus)
def execution_run_status(
    execution_id: str, _: User = Depends(require_user)
) -> ExecutionRunStatus:
    """Live durable Temporal workflow status for ``execution_id``."""
    settings = get_settings()
    url = (
        f"{settings.orchestrator_url.rstrip('/')}"
        f"/executions/{execution_id}/run-status"
    )
    data = _get_json(url, _headers("orchestrator_token"), "orchestrator_client")
    durable_status = "unknown"
    if isinstance(data, dict):
        durable_status = str(data.get("durable_status", "unknown"))
    return ExecutionRunStatus(
        execution_id=execution_id, durable_status=durable_status
    )
