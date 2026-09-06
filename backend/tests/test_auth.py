from datetime import timedelta

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.config import get_settings
from app.database import SessionLocal
from app.models import Role, User
from app.security import create_token


def test_login_and_current_user(client: TestClient) -> None:
    response = client.post(
        "/api/auth/token", data={"username": "viewer", "password": "viewer-test-password"}
    )
    assert response.status_code == 200
    assert response.json()["expires_in"] == 1800
    me = client.get(
        "/api/auth/me", headers={"Authorization": f"Bearer {response.json()['access_token']}"}
    )
    assert me.json() == {
        "id": 1,
        "username": "viewer",
        "roles": ["viewer"],
        "permissions": ["directory:read"],
    }
    assert "password" not in me.text
    assert "no-store" in response.headers["cache-control"]


@pytest.mark.parametrize(
    "username,password",
    [("viewer", "wrong"), ("missing", "viewer-test-password"), ("hr", "x" * 1025)],
)
def test_invalid_credentials(client: TestClient, username: str, password: str) -> None:
    response = client.post("/api/auth/token", data={"username": username, "password": password})
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid username or password."


def test_missing_malformed_and_expired_tokens(client: TestClient) -> None:
    assert client.get("/api/people").status_code == 401
    assert (
        client.get("/api/people", headers={"Authorization": "Bearer nonsense"}).status_code == 401
    )
    with SessionLocal() as db:
        user = db.get(User, 2)
        assert user is not None
        token = create_token(user, lifetime=timedelta(seconds=-1))
    response = client.get("/api/people", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401
    assert "expired" in response.json()["detail"]


def test_roles_are_loaded_from_database(
    client: TestClient, headers: dict[str, dict[str, str]]
) -> None:
    token = headers["viewer"]["Authorization"].split()[1]
    # Even a validly signed token containing an extra HR role cannot grant access.
    claims = jwt.decode(
        token, get_settings().jwt_secret, algorithms=["HS256"], audience="team-directory-api"
    )
    claims.update(
        role="hr", roles=["viewer", "hr"], scope="records:write audit:read confidential:read"
    )
    token = jwt.encode(claims, get_settings().jwt_secret, algorithm="HS256")
    assert client.get("/api/audit", headers={"Authorization": f"Bearer {token}"}).status_code == 403
    with SessionLocal.begin() as db:
        user = db.get(User, 2)
        assert user is not None
        user.roles = list(db.scalars(select(Role).where(Role.name == "viewer")))
    assert client.get("/api/audit", headers=headers["hr"]).status_code == 403


def test_invalid_signature_missing_exp_and_deleted_user(
    client: TestClient, headers: dict[str, dict[str, str]]
) -> None:
    token = headers["viewer"]["Authorization"].split()[1]
    claims = jwt.decode(
        token, get_settings().jwt_secret, algorithms=["HS256"], audience="team-directory-api"
    )
    forged = jwt.encode(claims, "wrong-key-at-least-32-characters-long", algorithm="HS256")
    assert (
        client.get("/api/people", headers={"Authorization": f"Bearer {forged}"}).status_code == 401
    )
    claims.pop("exp")
    invalid = jwt.encode(claims, get_settings().jwt_secret, algorithm="HS256")
    assert (
        client.get("/api/people", headers={"Authorization": f"Bearer {invalid}"}).status_code == 401
    )
    with SessionLocal.begin() as db:
        db.delete(db.get(User, 1))
    assert client.get("/api/people", headers=headers["viewer"]).status_code == 401
