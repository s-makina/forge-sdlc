"""Terminal and test execution (subphase 3.5).

Runs build, test, and lint commands sourced from the project's technology
adapter inside the workspace container, capturing exit codes and output as
structured results (FR-7.1).
"""

from __future__ import annotations

import shlex
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.adapters.registry import Adapter, detect, get_adapter
from app.docker.client import DockerClient
from app.models.execution import Execution, ExecutionStatus
from app.services import events, workspace


@dataclass
class CommandResult:
    """Structured result of a single command run."""

    kind: str
    command: str
    exit_code: int
    output: str
    succeeded: bool


def resolve_adapter(execution: Execution) -> Adapter:
    """Detect the technology adapter from the repository marker files.

    If the execution declares an adapter, use it; otherwise fall back to
    rule-based detection over a minimal marker set.
    """
    adapter_name = getattr(execution, "adapter_name", None)
    if adapter_name:
        return get_adapter(adapter_name)
    markers = _marker_probe(execution)
    return detect(markers)


def _marker_probe(execution: Execution) -> list[str]:
    """Best-effort marker list derived from the repository metadata.

    In practice detection is performed on the checked-out tree (Phase 3.3); here
    we accept an explicit hint or the empty default.
    """
    hint = getattr(execution, "adapter_hint", None)
    if hint:
        return [hint]
    return []


def run_command(
    docker: DockerClient,
    execution: Execution,
    command: str,
    *,
    kind: str,
    workdir: str | None = None,
) -> CommandResult:
    """Run a single command inside the workspace container."""
    if not execution.container_id:
        raise RuntimeError("workspace container is not provisioned")

    # cd into the cloned repo directory (best-effort) before running. The
    # workdir is shell-quoted because it can be derived from caller/repo input.
    workdir = workdir or "/workspace"
    cmd = f"cd {shlex.quote(workdir)} && {command}"
    exit_code, output = docker.exec_run(execution.container_id, ["/bin/sh", "-c", cmd])
    return CommandResult(
        kind=kind,
        command=command,
        exit_code=exit_code,
        output=output,
        succeeded=exit_code == 0,
    )


def run_phase(
    db: Session,
    docker: DockerClient,
    execution: Execution,
    adapter: Adapter,
    phase: str,
    *,
    workdir: str | None = None,
) -> list[CommandResult]:
    """Run all commands for a phase (build/test/lint/install)."""
    commands = {
        "build": adapter.build,
        "test": adapter.test,
        "lint": adapter.lint,
        "install": adapter.install,
    }[phase]

    results: list[CommandResult] = []
    for command in commands:
        result = run_command(docker, execution, command, kind=phase, workdir=workdir)
        events.record_command(db, execution.execution_id, command, result.exit_code)
        results.append(result)
    return results


def run_tests(
    db: Session,
    docker: DockerClient,
    execution: Execution,
    adapter: Adapter | None = None,
    *,
    workdir: str | None = None,
) -> tuple[list[CommandResult], Execution]:
    """Run the adapter's test command and record the outcome.

    On any non-zero exit the execution is moved to ``failed``; otherwise it
    stays ``running`` (a later step commits or succeeds).
    """
    adapter = adapter or resolve_adapter(execution)
    results = run_phase(db, docker, execution, adapter, "test", workdir=workdir)

    if not all(r.succeeded for r in results):
        failed = next(r for r in results if not r.succeeded)
        summary = failed.output[-500:]
        execution = workspace.fail_execution(
            db, execution, f"tests failed ({failed.command}): {summary}"
        )
    return results, execution