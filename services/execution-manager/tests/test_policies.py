"""Resource and network policy tests for subphase 3.6."""

from datetime import datetime, timezone

import pytest
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.docker.client import ContainerSpec
from app.models.execution import Execution, ExecutionStatus
from app.schemas.execution import ExecutionCreate
from app.services import executor, executions, policies, workspace


def _execution(db: Session, **overrides: object) -> Execution:
    payload = {
        "project_id": 1,
        "repository_url": "https://github.com/example/app.git",
        "branch": "main",
    }
    payload.update(overrides)
    return executions.create_execution(db, ExecutionCreate(**payload))  # type: ignore[arg-type]


def test_resolve_policy_minimal_network(db_session: Session) -> None:
    execution = _execution(db_session)
    policy = policies.resolve_policy(execution, get_settings())

    assert policy.network_policy == "minimal"
    # Default allowlist includes package registries but not the docker socket.
    assert "pypi.org" in policy.network_allowlist
    assert "registry.npmjs.org" in policy.network_allowlist
    assert "host.docker.internal" not in policy.network_allowlist
    assert policy.run_as_non_root is True
    assert policy.mount_host_docker_socket is False


def test_resolve_policy_none_network(db_session: Session) -> None:
    execution = _execution(db_session, network_policy="none")
    policy = policies.resolve_policy(execution, get_settings())
    assert policy.network_allowlist == []


def test_resolve_policy_open_network(db_session: Session) -> None:
    execution = _execution(db_session, network_policy="open")
    policy = policies.resolve_policy(execution, get_settings())
    assert policy.network_allowlist == ["*"]


def test_resolve_policy_rejects_nonpositive_limits(db_session: Session) -> None:
    execution = _execution(db_session, cpu_limit=0)
    with pytest.raises(ValueError):
        policies.resolve_policy(execution, get_settings())


def test_validate_spec_rejects_docker_host(db_session: Session) -> None:
    execution = _execution(db_session)
    spec = workspace.build_spec(execution, get_settings())
    # Forcibly inject the docker socket host to simulate a misconfiguration.
    bad = ContainerSpec(
        name=spec.name,
        image=spec.image,
        working_dir=spec.working_dir,
        cpu_limit=spec.cpu_limit,
        memory_limit=spec.memory_limit,
        disk_limit=spec.disk_limit,
        network_policy=spec.network_policy,
        network_allowlist=["host.docker.internal"],
        environment=spec.environment,
        mounts=spec.mounts,
        command=spec.command,
    )
    with pytest.raises(ValueError):
        policies.validate_spec(bad)


def test_is_timed_out(db_session: Session) -> None:
    execution = _execution(db_session)
    assert policies.is_timed_out(execution, 0.0) is False  # not started

    execution.started_at = datetime.now(timezone.utc)
    # Within budget.
    assert policies.is_timed_out(execution, execution.started_at.timestamp() + 10) is False
    # Past budget.
    assert (
        policies.is_timed_out(execution, execution.started_at.timestamp() + execution.timeout_seconds + 1)
        is True
    )


def test_build_spec_uses_policy_allowlist(db_session: Session) -> None:
    execution = _execution(db_session, network_policy="minimal")
    spec = workspace.build_spec(execution, get_settings())
    assert "pypi.org" in spec.network_allowlist


def test_executor_check_timeout_fails_overdue(db_session: Session) -> None:
    execution = _execution(db_session)
    execution.status = ExecutionStatus.RUNNING.value
    execution.started_at = datetime.now(timezone.utc)
    # Set a tiny timeout so it is already overdue.
    execution.timeout_seconds = -1

    result = executor.check_timeout(db_session, execution)
    assert result.status == ExecutionStatus.FAILED.value
    assert "timed out" in (result.error_message or "")