"""Auth flow tests (login / logout / me) using the bootstrap operator path."""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.user import User


def _seed_operator(db: Session, email: str = "op@example.com", password: str = "secret") -> None:
    db.add(
        User(
            email=email,
            password_hash=hash_password(password),
            display_name="Operator",
            is_active=True,
            is_operator=True,
        )
    )
    db.commit()


def test_login_me_logout(client: TestClient, db_session: Session) -> None:
    _seed_operator(db_session)

    # Login
    res = client.post("/api/v1/auth/login", json={"email": "op@example.com", "password": "secret"})
    assert res.status_code == 200
    assert res.json()["is_operator"] is True

    # Session cookie now allows access
    me = client.get("/api/v1/auth/me")
    assert me.status_code == 200
    assert me.json()["is_authenticated"] is True

    # Logout clears it
    out = client.post("/api/v1/auth/logout")
    assert out.status_code == 200
    me2 = client.get("/api/v1/auth/me")
    assert me2.status_code == 200
    assert me2.json()["is_authenticated"] is False


def test_login_rejects_bad_password(client: TestClient, db_session: Session) -> None:
    _seed_operator(db_session)
    res = client.post(
        "/api/v1/auth/login", json={"email": "op@example.com", "password": "wrong"}
    )
    assert res.status_code == 401


def test_login_rejects_unknown_user(client: TestClient) -> None:
    res = client.post("/api/v1/auth/login", json={"email": "nobody@example.com", "password": "x"})
    assert res.status_code == 401
