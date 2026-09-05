"""Create directory and audit schema

Revision ID: 8c376084aca1
Revises:
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "8c376084aca1"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "classifications",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.CheckConstraint("length(trim(name)) > 0", name="classification_name_nonempty"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_table(
        "people",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("work_email", sa.String(length=254), nullable=False),
        sa.Column("department", sa.String(length=80), nullable=False),
        sa.Column("private_notes", sa.Text(), nullable=False),
        sa.CheckConstraint("length(trim(department)) > 0", name="department_nonempty"),
        sa.CheckConstraint("length(trim(name)) > 0", name="person_name_nonempty"),
        sa.CheckConstraint("work_email = lower(work_email)", name="email_lowercase"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("work_email"),
    )
    op.create_index(op.f("ix_people_department"), "people", ["department"], unique=False)
    op.create_index(
        "ix_people_name_lower", "people", [sa.literal_column("lower(name)")], unique=False
    )
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("username", sa.String(length=80), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.CheckConstraint("role IN ('viewer', 'hr')", name="user_role"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("username"),
    )
    op.create_table(
        "audit_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("actor_id", sa.Integer(), nullable=False),
        sa.Column("target_person_id", sa.Integer(), nullable=True),
        sa.Column("requested_person_id", sa.Integer(), nullable=False),
        sa.Column("action", sa.String(length=80), nullable=False),
        sa.Column("field_names", sa.JSON(), nullable=False),
        sa.Column(
            "timestamp", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column("outcome", sa.String(length=20), nullable=False),
        sa.CheckConstraint("outcome IN ('success', 'denied', 'not_found')", name="audit_outcome"),
        sa.ForeignKeyConstraint(
            ["actor_id"],
            ["users.id"],
        ),
        sa.ForeignKeyConstraint(
            ["target_person_id"],
            ["people.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_audit_events_actor_id"), "audit_events", ["actor_id"], unique=False)
    op.create_index(
        op.f("ix_audit_events_target_person_id"), "audit_events", ["target_person_id"], unique=False
    )
    op.create_index(op.f("ix_audit_events_timestamp"), "audit_events", ["timestamp"], unique=False)
    op.create_table(
        "compliance_records",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("person_id", sa.Integer(), nullable=False),
        sa.Column("requirement", sa.String(length=160), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("completion_date", sa.Date(), nullable=True),
        sa.Column("expiry_date", sa.Date(), nullable=True),
        sa.CheckConstraint(
            "(status = 'completed' AND completion_date IS NOT NULL) OR "
            "(status = 'pending' AND completion_date IS NULL AND expiry_date IS NULL)",
            name="compliance_completion",
        ),
        sa.CheckConstraint("status IN ('pending', 'completed')", name="compliance_status"),
        sa.CheckConstraint(
            "expiry_date IS NULL OR expiry_date >= completion_date", name="compliance_dates"
        ),
        sa.CheckConstraint("length(trim(requirement)) > 0", name="requirement_nonempty"),
        sa.ForeignKeyConstraint(
            ["person_id"],
            ["people.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("person_id", "requirement", name="uq_person_requirement"),
    )
    op.create_index(
        op.f("ix_compliance_records_person_id"), "compliance_records", ["person_id"], unique=False
    )
    op.create_table(
        "employments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("person_id", sa.Integer(), nullable=False),
        sa.Column("job_title", sa.String(length=120), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("classification_id", sa.Integer(), nullable=False),
        sa.Column("salary", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.CheckConstraint("status IN ('active', 'on_leave', 'ended')", name="employment_status"),
        sa.CheckConstraint("end_date IS NULL OR end_date >= start_date", name="employment_dates"),
        sa.CheckConstraint("length(trim(job_title)) > 0", name="job_title_nonempty"),
        sa.CheckConstraint("salary >= 0", name="salary_nonnegative"),
        sa.ForeignKeyConstraint(
            ["classification_id"],
            ["classifications.id"],
        ),
        sa.ForeignKeyConstraint(
            ["person_id"],
            ["people.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("person_id", "job_title", "start_date", name="uq_employment_record"),
    )
    op.create_index(
        op.f("ix_employments_classification_id"), "employments", ["classification_id"], unique=False
    )
    op.create_index(op.f("ix_employments_person_id"), "employments", ["person_id"], unique=False)
    op.create_index(op.f("ix_employments_status"), "employments", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_employments_status"), table_name="employments")
    op.drop_index(op.f("ix_employments_person_id"), table_name="employments")
    op.drop_index(op.f("ix_employments_classification_id"), table_name="employments")
    op.drop_table("employments")
    op.drop_index(op.f("ix_compliance_records_person_id"), table_name="compliance_records")
    op.drop_table("compliance_records")
    op.drop_index(op.f("ix_audit_events_timestamp"), table_name="audit_events")
    op.drop_index(op.f("ix_audit_events_target_person_id"), table_name="audit_events")
    op.drop_index(op.f("ix_audit_events_actor_id"), table_name="audit_events")
    op.drop_table("audit_events")
    op.drop_table("users")
    op.drop_index("ix_people_name_lower", table_name="people")
    op.drop_index(op.f("ix_people_department"), table_name="people")
    op.drop_table("people")
    op.drop_table("classifications")
