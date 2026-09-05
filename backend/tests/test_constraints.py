import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.database import engine


@pytest.mark.parametrize(
    "statement",
    [
        "UPDATE people SET work_email = 'jordan@example.com' WHERE id = 1",
        "UPDATE people SET work_email = 'Avery@example.com' WHERE id = 1",
        "UPDATE people SET name = ' ' WHERE id = 1",
        "UPDATE employments SET person_id = 999 WHERE id = 1",
        "UPDATE employments SET classification_id = 999 WHERE id = 1",
        "UPDATE employments SET salary = -1 WHERE id = 1",
        "UPDATE employments SET end_date = '2000-01-01' WHERE id = 1",
        "UPDATE employments SET status = 'invalid' WHERE id = 1",
        "UPDATE compliance_records SET status = 'completed' WHERE id = 1",
        "UPDATE compliance_records SET expiry_date = '2026-01-01' WHERE id = 1",
        "UPDATE compliance_records SET status = 'completed', completion_date = '2026-02-01', "
        "expiry_date = '2026-01-01' WHERE id = 1",
        "UPDATE users SET role = 'admin' WHERE id = 1",
        "DELETE FROM classifications WHERE id = 1",
        "INSERT INTO compliance_records (person_id, requirement, status) "
        "VALUES (1, 'Security training', 'pending')",
    ],
)
def test_database_enforces_constraints_independently_of_api(statement):
    with engine.connect() as connection:
        with pytest.raises(IntegrityError):
            connection.execute(text(statement))
        connection.rollback()


def test_migration_is_current():
    with engine.connect() as connection:
        assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
