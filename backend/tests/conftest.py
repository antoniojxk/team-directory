import os
from collections.abc import Iterator
from datetime import date
from pathlib import Path

import pytest
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.engine import make_url

from alembic import command

# Refuse to truncate the development or production database by mistake.
test_url = os.environ.get("TEST_DATABASE_URL", "")
if not test_url or not (make_url(test_url).database or "").endswith("_test"):
    raise RuntimeError("Set TEST_DATABASE_URL to a PostgreSQL database whose name ends in _test")
if make_url(test_url).get_backend_name() != "postgresql":
    raise RuntimeError("These integration tests require real PostgreSQL")
os.environ["FRONTEND_ORIGINS"] = '["https://team-directory.web.app"]'
os.environ["DATABASE_URL"] = test_url
os.environ.pop("DIRECT_DATABASE_URL", None)
os.environ["JWT_SECRET"] = "integration-tests-only-secret-with-more-than-32-characters"

from fastapi.testclient import TestClient  # noqa: E402

from app.database import SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models import (  # noqa: E402
    Classification,
    ComplianceRecord,
    Employment,
    Person,
    Role,
    User,
)
from app.security import create_token, password_hash  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def migrated_database() -> Iterator[None]:
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    command.upgrade(config, "head")
    yield
    engine.dispose()


@pytest.fixture(scope="session")
def hashes() -> tuple[str, str]:
    return password_hash.hash("viewer-test-password"), password_hash.hash("hr-test-password")


@pytest.fixture(autouse=True)
def records(migrated_database: None, hashes: tuple[str, str]) -> None:
    with engine.begin() as connection:
        connection.execute(
            text(
                "TRUNCATE audit_events, compliance_records, employments, people, "
                "classifications, users, roles RESTART IDENTITY CASCADE"
            )
        )
    with SessionLocal.begin() as db:
        viewer = Role(name="viewer")
        hr = Role(name="hr")
        db.add_all(
            [
                User(username="viewer", roles=[viewer], password_hash=hashes[0]),
                User(username="hr", roles=[hr], password_hash=hashes[1]),
            ]
        )
        db.add_all([Classification(name="employee"), Classification(name="contractor")])
        db.add_all(
            [
                Person(
                    name="Avery Chen",
                    work_email="avery@example.com",
                    department="Engineering",
                    private_notes="CONFIDENTIAL_NOTE_SENTINEL",
                ),
                Person(
                    name="Jordan Rivera",
                    work_email="jordan@example.com",
                    department="Design",
                    private_notes="OTHER_PRIVATE_NOTE",
                ),
                Person(
                    name="Riley Brooks",
                    work_email="riley@example.com",
                    department="Engineering",
                    private_notes="",
                ),
            ]
        )
        db.flush()
        db.add_all(
            [
                Employment(
                    person_id=1,
                    job_title="Developer",
                    start_date=date(2024, 1, 1),
                    status="active",
                    classification_id=1,
                    salary="91234.56",
                ),
                Employment(
                    person_id=1,
                    job_title="Former consultant",
                    start_date=date(2023, 1, 1),
                    end_date=date(2023, 12, 31),
                    status="ended",
                    classification_id=2,
                    salary="80000.00",
                ),
                Employment(
                    person_id=2,
                    job_title="Designer",
                    start_date=date(2024, 1, 1),
                    status="on_leave",
                    classification_id=2,
                    salary="75000.00",
                ),
                ComplianceRecord(person_id=1, requirement="Security training", status="pending"),
            ]
        )


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client


@pytest.fixture
def headers() -> dict[str, dict[str, str]]:
    with SessionLocal() as db:
        result = {}
        for i, role in [(1, "viewer"), (2, "hr")]:
            user = db.get(User, i)
            assert user is not None
            result[role] = {"Authorization": f"Bearer {create_token(user)}"}
        return result
