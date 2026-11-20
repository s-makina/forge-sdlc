"""Provider connectivity and capability probes.

Probes are performed on demand against each configured provider. The network
layer is isolated behind :class:`ProviderProbeClient` so tests can inject a fake
``httpx`` transport and never touch the network.

A probe returns one of three states:

- ``ok`` / ``error`` - the provider answered (or refused) the probe;
- ``unknown`` - no probe was attempted, or the endpoint does not expose a way to
  verify that capability (e.g. a models listing is unavailable).

Unknown is never treated as "supported" by the router.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

import httpx

from app.core.secrets import CredentialError, resolve_credential
from app.models.capabilities import ModelCapability
from app.models.model_provider import Model, ModelProvider, ProviderType

STATUS_OK = "ok"
STATUS_ERROR = "error"
STATUS_UNKNOWN = "unknown"


@dataclass(slots=True)
class ProbeResult:
    status: str
    latency_ms: float | None = None
    detail: str | None = None
    capabilities: dict[str, bool | None] = field(default_factory=dict)


def _auth_headers(provider: ModelProvider) -> dict[str, str]:
    secret = resolve_credential(provider.credential_ref)
    if secret:
        return {"Authorization": f"Bearer {secret}"}
    return {}


def _capability_set(models: list[Model]) -> dict[str, bool | None]:
    declared: dict[str, bool | None] = {}
    for model in models:
        for capability in model.capabilities:
            declared[capability] = True
    for capability in ModelCapability:
        declared.setdefault(capability.value, None)
    return declared


class ProviderProbeClient:
    """Performs probes against providers using an injectable httpx transport."""

    def __init__(self, transport: httpx.BaseTransport | None = None) -> None:
        self._transport = transport

    def _client(self, provider: ModelProvider) -> httpx.Client:
        return httpx.Client(
            base_url=provider.base_url,
            timeout=provider.timeout_seconds,
            transport=self._transport,
        )

    def connectivity(self, provider: ModelProvider) -> ProbeResult:
        started = time.perf_counter()
        try:
            headers = _auth_headers(provider)
            with self._client(provider) as client:
                if provider.provider_type == ProviderType.OLLAMA.value:
                    response = client.get("/api/tags")
                else:
                    response = client.get("/models", headers=headers)
        except (httpx.HTTPError, CredentialError) as exc:
            latency = (time.perf_counter() - started) * 1000
            return ProbeResult(status=STATUS_ERROR, latency_ms=latency, detail=type(exc).__name__)
        latency = (time.perf_counter() - started) * 1000
        if response.status_code >= 400:
            return ProbeResult(
                status=STATUS_ERROR,
                latency_ms=latency,
                detail=f"HTTP {response.status_code}",
            )
        return ProbeResult(status=STATUS_OK, latency_ms=latency)


def probe_capabilities(models: list[Model]) -> dict[str, bool | None]:
    """Return the declared capability status map for a set of models."""
    return _capability_set(models)
