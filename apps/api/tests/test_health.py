"""Health endpoint tests."""

from fastapi.testclient import TestClient


def test_health_ok(client: TestClient) -> None:
    res = client.get("/health")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok"
    assert "app" in body


def test_projects_requires_auth(client: TestClient) -> None:
    res = client.get("/api/v1/projects")
    assert res.status_code == 401
