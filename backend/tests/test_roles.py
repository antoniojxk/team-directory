import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text

from app.database import SessionLocal, engine
from app.models import AuditEvent, Role, User
from app.security import ROLE_PERMISSIONS, SCOPES


@pytest.mark.parametrize(
    "names,expected",
    [
        ([], []),
        (["unknown"], []),
        (["unknown", "viewer"], ["directory:read"]),
        (["viewer", "hr"], list(SCOPES)),
    ],
)
def test_role_sets_drive_api_and_audited_access(
    client: TestClient,
    headers: dict[str, dict[str, str]],
    names: list[str],
    expected: list[str],
) -> None:
    with SessionLocal.begin() as db:
        db.add(Role(name="unknown"))
        user = db.get(User, 1)
        assert user is not None
        user.roles = list(db.scalars(select(Role).where(Role.name.in_(names))))
    auth = headers["viewer"]  # Token predates assignment changes.
    me = client.get("/api/auth/me", headers=auth)
    assert me.status_code == 200
    assert me.json()["roles"] == sorted(names)
    assert me.json()["permissions"] == expected
    assert "role" not in me.json()
    assert client.get("/api/people", headers=auth).status_code == (200 if expected else 403)
    allowed = "confidential:read" in expected
    response = client.get("/api/people/1/confidential", headers=auth)
    assert response.status_code == (200 if allowed else 403)
    assert ("CONFIDENTIAL_NOTE_SENTINEL" in response.text) == allowed
    assert client.get("/api/audit", headers=auth).status_code == (200 if allowed else 403)
    with SessionLocal() as db:
        event = db.scalar(select(AuditEvent).where(AuditEvent.actor_id == 1))
        assert event is not None
        assert event.outcome == ("success" if allowed else "denied")


def test_permissions_are_unioned_across_complementary_roles(
    client: TestClient,
    headers: dict[str, dict[str, str]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Split the grants so choosing only either role would fail this regression.
    monkeypatch.setitem(ROLE_PERMISSIONS, "hr", ["records:write", "confidential:read"])
    with SessionLocal.begin() as db:
        user = db.get(User, 1)
        assert user is not None
        user.roles = list(db.scalars(select(Role)))
    auth = headers["viewer"]
    assert client.get("/api/auth/me", headers=auth).json()["permissions"] == [
        "directory:read",
        "records:write",
        "confidential:read",
    ]
    assert client.get("/api/people", headers=auth).status_code == 200
    assert (
        client.post("/api/classifications", headers=auth, json={"name": "temp"}).status_code == 201
    )
    assert client.get("/api/people/1/confidential", headers=auth).status_code == 200
    assert client.get("/api/audit", headers=auth).status_code == 403


def test_revoking_one_of_multiple_roles_takes_effect_on_existing_token(
    client: TestClient, headers: dict[str, dict[str, str]]
) -> None:
    with SessionLocal.begin() as db:
        user = db.get(User, 2)
        assert user is not None
        user.roles = list(db.scalars(select(Role)))
    auth = headers["hr"]
    assert client.get("/api/audit", headers=auth).status_code == 200
    with engine.begin() as connection:
        connection.execute(
            text(
                "DELETE FROM user_roles WHERE user_id = 2 "
                "AND role_id = (SELECT id FROM roles WHERE name = 'hr')"
            )
        )
    assert client.get("/api/auth/me", headers=auth).json()["roles"] == ["viewer"]
    assert client.get("/api/people", headers=auth).status_code == 200
    assert client.get("/api/audit", headers=auth).status_code == 403
    assert client.get("/api/people/1/confidential", headers=auth).status_code == 403
    assert (
        client.post("/api/classifications", headers=auth, json={"name": "temp"}).status_code == 403
    )


def test_deleting_users_or_roles_cleans_up_only_their_assignments() -> None:
    with engine.begin() as connection:
        connection.execute(text("DELETE FROM users WHERE id = 1"))
        assert connection.execute(text("SELECT count(*) FROM user_roles")).scalar_one() == 1
        assert connection.execute(text("SELECT count(*) FROM roles")).scalar_one() == 2
        connection.execute(text("DELETE FROM roles WHERE name = 'hr'"))
        assert connection.execute(text("SELECT count(*) FROM user_roles")).scalar_one() == 0
        assert connection.execute(text("SELECT count(*) FROM users")).scalar_one() == 1
