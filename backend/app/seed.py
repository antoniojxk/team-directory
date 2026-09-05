"""Idempotent demo data. Existing people and account passwords are never overwritten."""

from datetime import date
from decimal import Decimal

from sqlalchemy import select

from app.config import get_settings
from app.database import SessionLocal
from app.models import Classification, ComplianceRecord, Employment, Person, User
from app.security import password_hash

PEOPLE = [
    ("Avery Chen", "Engineering", "Backend Developer", "employee"),
    ("Jordan Rivera", "Design", "Product Designer", "employee"),
    ("Morgan Ellis", "People", "People Partner", "employee"),
    ("Riley Brooks", "Engineering", "QA Specialist", "contractor"),
    ("Samira Patel", "Operations", "Operations Analyst", "employee"),
    ("Theo Laurent", "Design", "Design Intern", "intern"),
    ("Alex Kim", "Engineering", "Platform Developer", "employee"),
    ("Casey Nguyen", "Operations", "Project Coordinator", "contractor"),
    ("Drew Campbell", "People", "Recruiting Coordinator", "employee"),
    ("Emery Silva", "Engineering", "Software Intern", "intern"),
    ("Finley Reed", "Design", "Content Designer", "employee"),
    ("Harper Okafor", "Operations", "Business Analyst", "employee"),
    ("Indigo Martin", "Engineering", "API Developer", "contractor"),
    ("Jules Ahmed", "People", "Learning Coordinator", "employee"),
    ("Kai Thompson", "Operations", "Support Specialist", "employee"),
    ("Logan Park", "Design", "UX Researcher", "contractor"),
    ("Mika Torres", "Engineering", "Data Developer", "employee"),
    ("Noor Bennett", "People", "People Intern", "intern"),
]


def seed() -> None:
    settings = get_settings()
    with SessionLocal.begin() as db:
        for role, password in [
            ("viewer", settings.demo_viewer_password),
            ("hr", settings.demo_hr_password),
        ]:
            if not db.scalar(select(User).where(User.username == role)):
                if password is None or not 12 <= len(password) <= 1024:
                    raise ValueError(f"Set DEMO_{role.upper()}_PASSWORD to 12–1024 characters")
                db.add(User(username=role, role=role, password_hash=password_hash.hash(password)))
        for name in ["employee", "contractor", "intern"]:
            if not db.scalar(select(Classification).where(Classification.name == name)):
                db.add(Classification(name=name))
        db.flush()
        classes = {c.name: c.id for c in db.scalars(select(Classification))}
        for i, (name, department, title, classification) in enumerate(PEOPLE):
            email = name.lower().replace(" ", ".") + "@example.com"
            if db.scalar(select(Person).where(Person.work_email == email)):
                continue
            person = Person(
                name=name,
                department=department,
                work_email=email,
                private_notes="Synthetic demo note: development plan review in October.",
            )
            db.add(person)
            db.flush()
            db.add(
                Employment(
                    person_id=person.id,
                    job_title=title,
                    start_date=date(2024 + i % 2, 1 + i % 9, 15),
                    end_date=date(2026, 6, 30) if i == 15 else None,
                    status="ended" if i == 15 else "on_leave" if i == 4 else "active",
                    classification_id=classes[classification],
                    salary=Decimal(55000 + i * 1750),
                )
            )
            db.add(
                ComplianceRecord(
                    person_id=person.id,
                    requirement="Information security fundamentals",
                    status="completed" if i % 3 else "pending",
                    completion_date=date(2026, 2, 12) if i % 3 else None,
                    expiry_date=date(2027, 2, 12) if i % 3 else None,
                )
            )
    print("Demo data ready. Existing records and passwords preserved.")


if __name__ == "__main__":
    seed()
