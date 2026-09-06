from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    JSON,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Table,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Person(Base):
    __tablename__ = "people"
    __table_args__ = (
        CheckConstraint("length(trim(name)) > 0", name="person_name_nonempty"),
        CheckConstraint("length(trim(department)) > 0", name="department_nonempty"),
        CheckConstraint("work_email = lower(work_email)", name="email_lowercase"),
        Index("ix_people_name_lower", text("lower(name)")),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    work_email: Mapped[str] = mapped_column(String(254), unique=True)
    department: Mapped[str] = mapped_column(String(80), index=True)
    private_notes: Mapped[str] = mapped_column(Text, default="")
    employments: Mapped[list["Employment"]] = relationship(order_by="Employment.start_date.desc()")
    compliance_records: Mapped[list["ComplianceRecord"]] = relationship(
        order_by="ComplianceRecord.id"
    )


class Classification(Base):
    __tablename__ = "classifications"
    __table_args__ = (
        CheckConstraint("length(trim(name)) > 0", name="classification_name_nonempty"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True)


class Employment(Base):
    __tablename__ = "employments"
    __table_args__ = (
        CheckConstraint("end_date IS NULL OR end_date >= start_date", name="employment_dates"),
        CheckConstraint("status IN ('active', 'on_leave', 'ended')", name="employment_status"),
        CheckConstraint("salary >= 0", name="salary_nonnegative"),
        CheckConstraint("length(trim(job_title)) > 0", name="job_title_nonempty"),
        UniqueConstraint("person_id", "job_title", "start_date", name="uq_employment_record"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    person_id: Mapped[int] = mapped_column(ForeignKey("people.id"), index=True)
    job_title: Mapped[str] = mapped_column(String(120))
    start_date: Mapped[date]
    end_date: Mapped[date | None]
    status: Mapped[str] = mapped_column(String(20), index=True)
    classification_id: Mapped[int] = mapped_column(ForeignKey("classifications.id"), index=True)
    salary: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    classification: Mapped[Classification] = relationship(lazy="joined")


class ComplianceRecord(Base):
    __tablename__ = "compliance_records"
    __table_args__ = (
        UniqueConstraint("person_id", "requirement", name="uq_person_requirement"),
        CheckConstraint("status IN ('pending', 'completed')", name="compliance_status"),
        CheckConstraint(
            "(status = 'completed' AND completion_date IS NOT NULL) OR "
            "(status = 'pending' AND completion_date IS NULL AND expiry_date IS NULL)",
            name="compliance_completion",
        ),
        CheckConstraint(
            "expiry_date IS NULL OR expiry_date >= completion_date", name="compliance_dates"
        ),
        CheckConstraint("length(trim(requirement)) > 0", name="requirement_nonempty"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    person_id: Mapped[int] = mapped_column(ForeignKey("people.id"), index=True)
    requirement: Mapped[str] = mapped_column(String(160))
    status: Mapped[str] = mapped_column(String(20))
    completion_date: Mapped[date | None]
    expiry_date: Mapped[date | None]


user_roles = Table(
    "user_roles",
    Base.metadata,
    Column("user_id", ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("role_id", ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True, index=True),
)


class Role(Base):
    __tablename__ = "roles"
    __table_args__ = (
        CheckConstraint("length(trim(name)) > 0", name="role_name_nonempty"),
        CheckConstraint("name = lower(trim(name))", name="role_name_normalized"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(80), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    roles: Mapped[list[Role]] = relationship(
        secondary=user_roles, lazy="selectin", order_by="Role.name"
    )


class AuditEvent(Base):
    __tablename__ = "audit_events"
    __table_args__ = (
        CheckConstraint("outcome IN ('success', 'denied', 'not_found')", name="audit_outcome"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    actor_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    target_person_id: Mapped[int | None] = mapped_column(ForeignKey("people.id"), index=True)
    requested_person_id: Mapped[int]
    action: Mapped[str] = mapped_column(String(80))
    field_names: Mapped[list[str]] = mapped_column(JSON)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    outcome: Mapped[str] = mapped_column(String(20))
    actor: Mapped[User] = relationship(lazy="joined")
