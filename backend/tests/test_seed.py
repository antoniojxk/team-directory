from sqlalchemy import func, select

from app.config import get_settings
from app.database import SessionLocal
from app.models import Classification, ComplianceRecord, Employment, Person, User
from app.seed import seed


def test_seed_is_repeatable_and_preserves_existing_edits_and_passwords(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "demo_viewer_password", "replacement-viewer-password")
    monkeypatch.setattr(settings, "demo_hr_password", "replacement-hr-password")
    with SessionLocal() as db:
        original_hash = db.get(User, 1).password_hash
    seed()
    with SessionLocal.begin() as db:
        person = db.scalar(select(Person).where(Person.work_email == "avery.chen@example.com"))
        person.private_notes = "Preserve this synthetic edit"
        counts = [
            db.scalar(select(func.count()).select_from(model))
            for model in [Person, Employment, ComplianceRecord, Classification, User]
        ]
    seed()
    with SessionLocal() as db:
        assert counts == [
            db.scalar(select(func.count()).select_from(model))
            for model in [Person, Employment, ComplianceRecord, Classification, User]
        ]
        assert db.get(User, 1).password_hash == original_hash
        assert (
            db.scalar(
                select(Person).where(Person.work_email == "avery.chen@example.com")
            ).private_notes
            == "Preserve this synthetic edit"
        )
