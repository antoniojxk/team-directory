"""Reset only an explicitly named test database, migrate, then seed browser fixtures."""

import os
import sys
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "backend"))
url = os.environ["DATABASE_URL"]
parsed = make_url(url)
if parsed.get_backend_name() != "postgresql" or not (parsed.database or "").endswith(
    "_test"
):
    raise RuntimeError("Browser setup only resets PostgreSQL databases ending in _test")

from alembic import command
from alembic.config import Config
from app.seed import seed

command.upgrade(Config(str(root / "backend" / "alembic.ini")), "head")
engine = create_engine(url, hide_parameters=True)
with engine.begin() as connection:
    connection.execute(
        text(
            "TRUNCATE audit_events, compliance_records, employments, people, "
            "classifications, users RESTART IDENTITY CASCADE"
        )
    )
engine.dispose()
seed()
