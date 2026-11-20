"""Model provider, routing and LiteLLM gateway tests."""

from __future__ import annotations

import os

import httpx
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import codec, hash_password
from app.models.user import User
from app.services import provider_health, seeds


def _login(client: TestClient, db: Session) -> None:
    user = User(
        email="models-tester@example.com",
        password_hash=hash_password("secret"),
        display_name="Models Tester",
        is_active=True,
        is_operator=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    client.cookies.set(get_settings().session_cookie_name, codec.create(user.id))


def _seed_models(db: Session) -> None:
    seeds.seed_default_providers(db, get_settings())
    seeds.seed_registries(db)


def _provider(db: Session, provider_id: int):
    from app.services.model_providers import get_provider

    return get_provider(db, provider_id)


def test_default_providers_and_profiles_seeded(client: TestClient, db_session: Session) -> None:
    _login(client, db_session)
    _seed_models(db_session)

    res = client.get("/api/v1/models/providers")
    assert res.status_code == 200
    providers = {p["name"]: p for p in res.json()["items"]}
    assert "ollama-local" in providers
    assert providers["ollama-local"]["provider_type"] == "ollama"

    res = client.get("/api/v1/models/profiles")
    assert res.status_code == 200
    profiles = {p["name"] for p in res.json()["items"]}
    assert {"coding-strong", "coding-fast", "review-specialist", "vision"} <= profiles


def test_provider_credential_ref_kept_as_reference(client: TestClient, db_session: Session) -> None:
    _login(client, db_session)
    _seed_models(db_session)

    res = client.post(
        "/api/v1/models/providers",
        json={
            "name": "ext",
            "provider_type": "openai-compatible",
            "base_url": "https://api.example.com/v1",
            "credential_ref": "env:EXT_API_KEY",
        },
    )
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["credential_ref"] == "env:EXT_API_KEY"
    assert "sk-" not in res.text

    provider_id = body["id"]

    os.environ["EXT_API_KEY"] = "sk-SECRET"
    try:
        model = client.post(
            f"/api/v1/models/providers/{provider_id}/models",
            json={"name": "my-model", "capabilities": ["chat", "tool_calling"]},
        )
        assert model.status_code == 201, model.text

        config = client.get("/api/v1/models/gateway/config").json()["config"]
        entry = next(
            e for e in config["model_list"] if e["model_name"] == "my-model"
        )
        params = entry["litellm_params"]
        assert params["model"] == "openai/my-model"
        assert params["api_key"] == "os.environ/EXT_API_KEY"
        assert "sk-SECRET" not in client.get("/api/v1/models/gateway/config").text
    finally:
        os.environ.pop("EXT_API_KEY", None)


def test_routing_resolves_capable_model_and_rejects_unconfigured(
    client: TestClient, db_session: Session
) -> None:
    _login(client, db_session)
    _seed_models(db_session)

    res = client.post(
        "/api/v1/models/providers/1/models",
        json={
            "name": "coding-model",
            "capabilities": ["chat", "tool_calling", "structured_output"],
        },
    )
    assert res.status_code == 201, res.text
    model_id = res.json()["id"]

    res = client.get("/api/v1/models/profiles")
    coding = next(p for p in res.json()["items"] if p["name"] == "coding-strong")
    res = client.patch(f"/api/v1/models/profiles/{coding['id']}", json={"primary_model_id": model_id})
    assert res.status_code == 200, res.text

    resolve = client.get("/api/v1/models/profiles/coding-strong/resolve")
    assert resolve.status_code == 200, resolve.text
    assert resolve.json()["model"]["name"] == "coding-model"
    assert resolve.json()["used_fallback"] is False

    # vision profile has no configured model -> clear failure (RoutingError).
    vision = client.get("/api/v1/models/profiles/vision/resolve")
    assert vision.status_code == 409
    assert "no models are configured" in vision.text


def test_routing_uses_only_capable_fallback(client: TestClient, db_session: Session) -> None:
    _login(client, db_session)
    _seed_models(db_session)

    capable = client.post(
        "/api/v1/models/providers/1/models",
        json={"name": "tool-model", "capabilities": ["chat", "tool_calling", "structured_output"]},
    ).json()["id"]
    incapable = client.post(
        "/api/v1/models/providers/1/models",
        json={"name": "plain-model", "capabilities": ["chat"]},
    ).json()["id"]

    coding = next(
        p
        for p in client.get("/api/v1/models/profiles").json()["items"]
        if p["name"] == "coding-strong"
    )
    res = client.patch(
        f"/api/v1/models/profiles/{coding['id']}",
        json={"primary_model_id": incapable, "fallback_model_ids": [capable]},
    )
    assert res.status_code == 200

    resolve = client.get("/api/v1/models/profiles/coding-strong/resolve")
    assert resolve.status_code == 200, resolve.text
    assert resolve.json()["used_fallback"] is True
    assert resolve.json()["model"]["name"] == "tool-model"


def test_connectivity_probe_with_fake_transport(db_session: Session) -> None:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, json={"models": []})
    )
    client = provider_health.ProviderProbeClient(transport=transport)
    provider = _provider(db_session, 1)
    if provider is None:
        return
    result = client.connectivity(provider)
    assert result.status == "ok"


def test_usage_recording_and_summary(client: TestClient, db_session: Session) -> None:
    _login(client, db_session)
    res = client.post(
        "/api/v1/models/usage",
        json={
            "profile_name": "coding-strong",
            "input_tokens": 100,
            "output_tokens": 40,
            "cost_usd": 0.01,
        },
    )
    assert res.status_code == 201, res.text
    assert res.json()["total_tokens"] == 140

    summary = client.get("/api/v1/models/usage").json()
    assert summary["total_calls"] == 1
    assert summary["input_tokens"] == 100
    assert summary["output_tokens"] == 40
