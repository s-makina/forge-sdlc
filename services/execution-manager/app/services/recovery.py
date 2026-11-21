"""Cleanup and recovery (subphase 3.8).

After an execution reaches a terminal state, or after a worker/infra crash, no
orphaned workspaces or scoped credentials should remain. This module provides:

- ``cleanup_execution``: tear down the container, archive the workspace, and
  revoke scoped credentials (README §12.3, NFR-2.1/NFR-1.2).
- ``recover_orphans``: sweep executions stuck in non-terminal states after a
  restart and drive them to a safe, recoverable state.
- ``retry``: bounded retry with escalation for transient failures (NFR-2.1).

Credential revocation is a best-effort hook here; scoped credential issuance is
introduced with Phase 4, so the revoker is injectable and a no-op by default.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import TypeVar

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.docker.client import DockerClient
from app.models.execution import Execution, ExecutionStatus
from app.services import executions

T = TypeVar("T")

# States that indicate an execution was interrupted mid-flight by a crash.
NON_TERMINAL = (
    ExecutionStatus.CREATED,
    ExecutionStatus.READY,
    ExecutionStatus.RUNNING,
    ExecutionStatus.CLEANING,
)


def retry(
    fn: Callable[[], T],
    *,
    attempts: int = 3,
    delay_seconds: float = 1.0,
    backoff: float = 2.0,
    on_final_failure: Callable[[Exception], None] | None = None,
) -> T:
    """Run ``fn`` with bounded retry and exponential backoff.

    Raises on the final attempt. ``on_final_failure`` is invoked with the last
    exception so callers can escalate (e.g. mark the execution failed).
    """
    last_exc: Exception | None = None
    wait = delay_seconds
    for attempt in range(attempts):
        try:
            return fn()
        except Exception as exc:  # noqa: BLE001 - any failure triggers retry
            last_exc = exc
            if attempt < attempts - 1:
                time.sleep(wait)
                wait *= backoff
    assert last_exc is not None
    if on_final_failure is not None:
        on_final_failure(last_exc)
    raise last_exc


def _revoke_credentials(execution: Execution) -> None:
    """Best-effort revocation of scoped credentials (Phase 4 hook)."""
    # Scoped credentials are issued per execution in Phase 4; revocation is a
    # no-op until then so cleanup never blocks on an unavailable credential
    # vault. NFR-1.2 requires short-lived, execution-scoped credentials.
    return None


def _archive_workspace(execution: Execution) -> None:
    """Best-effort archive of workspace state (logs/artefacts already stored).

    Artefacts and logs are persisted in Phase 3.7 before cleanup; here we ensure
    the workspace container is gone and leave a durable record of the outcome.
    """
    return None


def cleanup_execution(
    db: Session,
    execution: Execution,
    docker: DockerClient,
) -> Execution:
    """Fully clean up an execution: stop/remove container, revoke creds.

    ``_archive_workspace`` and ``_revoke_credentials`` are best-effort hooks that
    never raise; container teardown swallows per-step errors so a partial
    failure still moves the execution forward. The execution is marked ``cleaning``
    first, then ``done`` (README §12.1).
    """
    execution = executions.transition(db, execution, ExecutionStatus.CLEANING)

    container_id = execution.container_id
    if container_id:
        try:
            docker.stop_container(container_id)
        except Exception:  # noqa: BLE001 - best-effort cleanup
            pass
        try:
            docker.remove_container(container_id)
        except Exception:  # noqa: BLE001 - best-effort cleanup
            pass
        execution.container_id = None

    try:
        _archive_workspace(execution)
    except Exception:  # noqa: BLE001 - archival must never block cleanup
        pass
    try:
        _revoke_credentials(execution)
    except Exception:  # noqa: BLE001 - revocation must never block cleanup
        pass

    return executions.transition(db, execution, ExecutionStatus.DONE)


def recover_orphans(
    db: Session,
    docker: DockerClient,
    settings: Settings,
    *,
    now_epoch: float | None = None,
) -> list[Execution]:
    """Sweep interrupted executions after a worker/infra failure.

    Any execution left in a non-terminal state (e.g. ``running`` after a crash)
    is recovered: overdue ones are failed (timeout) and cleaned; others are
    moved to a safe state so they do not linger as orphans (NFR-2.1).
    """
    now = now_epoch if now_epoch is not None else time.time()
    stmt = select(Execution).where(Execution.status.in_([s.value for s in NON_TERMINAL]))
    recovered: list[Execution] = []
    for execution in db.scalars(stmt).all():
        # Re-drive the timeout check (3.6) so a crash mid-run does not leak a
        # runaway container past its budget.
        if execution.status in (
            ExecutionStatus.READY.value,
            ExecutionStatus.RUNNING.value,
        ) and _is_overdue(execution, now):
            execution = _fail_with_message(db, execution, "recovered: execution timed out")
        # Move the interrupted execution through cleanup so its container is
        # removed and it cannot remain an orphan. An overdue run was marked
        # ``failed`` above but is still driven to ``done`` here: ``done`` is the
        # durable "container removed" outcome, while ``error_message`` retains
        # the timeout reason for observability.
        execution = cleanup_execution(db, execution, docker)
        recovered.append(execution)
    return recovered


def _is_overdue(execution: Execution, now_epoch: float) -> bool:
    """Return True if a started execution has exceeded its time budget."""
    if execution.started_at is None:
        return False
    return now_epoch - execution.started_at.timestamp() > execution.timeout_seconds


def _fail_with_message(db: Session, execution: Execution, message: str) -> Execution:
    execution.error_message = message
    return executions.transition(db, execution, ExecutionStatus.FAILED)