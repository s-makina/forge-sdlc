"""Resource and network policy enforcement (subphase 3.6).

Formalises the workspace limits (README §12.2/§12.3, NFR-1):
CPU, memory, disk, and time caps; network access restricted by policy (default
minimal, with an allowlist for package registries); non-root execution; and
never mounting the host Docker socket into agent containers.

The container spec builder (subphase 3.2) already applies the mechanical limits
(nano_cpus, mem_limit, pids_limit, non-root user, read-only rootfs). This module
validates policy inputs, computes the network allowlist, and provides the
timeout check the executor uses to cap runaway runs.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.core.config import Settings
from app.docker.client import ContainerSpec
from app.models.execution import Execution

# Package registries allowed under the "minimal" policy (README §12.3).
DEFAULT_REGISTRIES: tuple[str, ...] = (
    "pypi.org",
    "files.pythonhosted.org",
    "registry.npmjs.org",
    "registry.yarnpkg.com",
    "github.com",
    "objects.githubusercontent.com",
    "codeload.github.com",
    "repo.maven.apache.org",
    "packagist.org",
)

# Hosts an agent container must NEVER reach (NFR-1.3, README §12.3).
FORBIDDEN_HOSTS: tuple[str, ...] = (
    "host.docker.internal",
    "127.0.0.1",
    "localhost",
    "0.0.0.0",
)


@dataclass(frozen=True)
class Policy:
    """Validated, resolved policy for an execution workspace."""

    image: str
    cpu_limit: float
    memory_limit: str
    disk_limit: str
    timeout_seconds: int
    network_policy: str
    network_allowlist: list[str]
    run_as_non_root: bool = True
    mount_host_docker_socket: bool = False


def resolve_policy(execution: Execution, settings: Settings) -> Policy:
    """Resolve and validate an execution's policy against settings."""
    network_policy = execution.network_policy or settings.workspace_network_policy
    allowlist = _resolve_allowlist(network_policy, settings)

    if execution.cpu_limit <= 0:
        raise ValueError("cpu_limit must be positive")
    if execution.timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be positive")

    return Policy(
        image=execution.image,
        cpu_limit=execution.cpu_limit,
        memory_limit=execution.memory_limit,
        disk_limit=execution.disk_limit,
        timeout_seconds=execution.timeout_seconds,
        network_policy=network_policy,
        network_allowlist=allowlist,
    )


def _resolve_allowlist(network_policy: str, settings: Settings) -> list[str]:
    """Compute the effective host allowlist for a network policy."""
    configured = [h.strip() for h in settings.workspace_network_allowlist.split(",") if h.strip()]
    if network_policy == "open":
        return ["*"]
    if network_policy == "none":
        return []
    # minimal (default): package registries plus any configured hosts.
    allowlist = list(DEFAULT_REGISTRIES)
    allowlist.extend(configured)
    return allowlist


def validate_spec(spec: ContainerSpec) -> None:
    """Reject specs that violate non-negotiable security requirements."""
    forbidden = [h for h in FORBIDDEN_HOSTS if h in spec.network_allowlist]
    if forbidden:
        raise ValueError(f"forbidden host in allowlist: {forbidden}")


def is_timed_out(execution: Execution, now_epoch: float) -> bool:
    """Return True if the execution has exceeded its time budget."""
    if execution.started_at is None:
        return False
    elapsed = now_epoch - execution.started_at.timestamp()
    return elapsed > execution.timeout_seconds