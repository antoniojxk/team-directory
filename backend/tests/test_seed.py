import pytest
from sqlalchemy import func, select

from app.config import get_settings
from app.database import SessionLocal
from app.models import Classification, ComplianceRecord, Employment, Person, Role, User
from app.seed import seed


@pytest.mark.parametrize("names", [["hr", "viewer"], []])
def test_seed_is_repeatable_and_preserves_existing_edits_and_passwords(
    monkeypatch: pytest.MonkeyPatch,
    names: list[str],
) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "demo_viewer_password", "replacement-viewer-password")
    monkeypatch.setattr(settings, "demo_hr_password", "replacement-hr-password")
    with SessionLocal.begin() as db:
        user = db.get(User, 1)
        assert user is not None
        original_hash = user.password_hash
        user.roles = list(db.scalars(select(Role).where(Role.name.in_(names))))
    seed()
    with SessionLocal.begin() as db:
        person = db.scalar(select(Person).where(Person.work_email == "avery.chen@example.com"))
        assert person is not None
        person.private_notes = "Preserve this synthetic edit"
        counts = [
            db.scalar(select(func.count()).select_from(model))
            for model in [
                Person,
                Employment,
                ComplianceRecord,
                Classification,
                User,
                Role,
            ]
        ]
    seed()
    with SessionLocal() as db:
        assert counts == [
            db.scalar(select(func.count()).select_from(model))
            for model in [
                Person,
                Employment,
                ComplianceRecord,
                Classification,
                User,
                Role,
            ]
        ]
        user = db.get(User, 1)
        assert user is not None
        assert user.password_hash == original_hash
        assert [role.name for role in user.roles] == names
        person = db.scalar(select(Person).where(Person.work_email == "avery.chen@example.com"))
        assert person is not None
        assert person.private_notes == "Preserve this synthetic edit"
