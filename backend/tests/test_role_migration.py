from pathlib import Path

import pytest
from alembic.config import Config
from sqlalchemy import inspect, text
from sqlalchemy.exc import DBAPIError

from alembic import command
from app.database import engine

PREVIOUS = "8c376084aca1"
CURRENT = "b719d2e4a630"


def config() -> Config:
    return Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))


def test_migration_round_trip_preserves_users_assignments_and_audits() -> None:
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO audit_events (actor_id, target_person_id, requested_person_id, "
                "action, field_names, outcome) "
                "VALUES (1, 1, 1, 'confidential.read', '[]', 'denied')"
            )
        )
        users = connection.execute(
            text("SELECT id, username, password_hash FROM users ORDER BY id")
        ).all()
    try:
        command.downgrade(config(), PREVIOUS)
        with engine.begin() as connection:
            assert connection.execute(
                text("SELECT role FROM users ORDER BY id")
            ).scalars().all() == ["viewer", "hr"]
            # A real legacy-schema insertion, independent of the new ORM model.
            connection.execute(
                text(
                    "INSERT INTO users (username, password_hash, role) "
                    "VALUES ('legacy', 'preserved-hash', 'hr')"
                )
            )
        command.upgrade(config(), "head")
        with engine.connect() as connection:
            assert (
                connection.execute(
                    text("SELECT id, username, password_hash FROM users WHERE id <= 2 ORDER BY id")
                ).all()
                == users
            )
            assert connection.execute(
                text(
                    "SELECT users.username, roles.name FROM users "
                    "JOIN user_roles ON user_roles.user_id = users.id "
                    "JOIN roles ON roles.id = user_roles.role_id ORDER BY users.id"
                )
            ).tuples().all() == [("viewer", "viewer"), ("hr", "hr"), ("legacy", "hr")]
            assert (
                connection.execute(
                    text("SELECT password_hash FROM users WHERE username = 'legacy'")
                ).scalar_one()
                == "preserved-hash"
            )
            assert connection.execute(text("SELECT actor_id, outcome FROM audit_events")).one() == (
                1,
                "denied",
            )
            assert "role" not in {
                column["name"] for column in inspect(connection).get_columns("users")
            }
        command.check(config())
    finally:
        command.upgrade(config(), "head")


@pytest.mark.parametrize(
    "statement",
    [
        "INSERT INTO user_roles (user_id, role_id) SELECT 1, id FROM roles WHERE name = 'hr'",
        "DELETE FROM user_roles WHERE user_id = 1",
        "INSERT INTO roles (name) VALUES ('custom')",
    ],
)
def test_downgrade_refuses_unrepresentable_data_without_changing_schema(statement: str) -> None:
    with engine.begin() as connection:
        connection.execute(text(statement))
        before = connection.execute(
            text("SELECT user_id, role_id FROM user_roles ORDER BY user_id, role_id")
        ).all()
    with pytest.raises(DBAPIError, match="Cannot downgrade"):
        command.downgrade(config(), PREVIOUS)
    with engine.connect() as connection:
        assert (
            connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
            == CURRENT
        )
        assert (
            connection.execute(
                text("SELECT user_id, role_id FROM user_roles ORDER BY user_id, role_id")
            ).all()
            == before
        )
        assert "role" not in {column["name"] for column in inspect(connection).get_columns("users")}
