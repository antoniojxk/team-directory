"""Separate roles and preserve existing user assignments.

Revision ID: b719d2e4a630
Revises: 8c376084aca1
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "b719d2e4a630"
down_revision: str | None = "8c376084aca1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "roles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.CheckConstraint("length(trim(name)) > 0", name="role_name_nonempty"),
        sa.CheckConstraint("name = lower(trim(name))", name="role_name_normalized"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_table(
        "user_roles",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("role_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id", "role_id"),
    )
    op.create_index("ix_user_roles_role_id", "user_roles", ["role_id"])
    op.execute("INSERT INTO roles (name) VALUES ('viewer'), ('hr')")
    op.execute(
        "INSERT INTO user_roles (user_id, role_id) "
        "SELECT users.id, roles.id FROM users JOIN roles ON roles.name = users.role"
    )
    op.drop_constraint("user_role", "users", type_="check")
    op.drop_column("users", "role")


def downgrade() -> None:
    # The old schema cannot represent multiple/no assignments or custom roles.
    # Fail transactionally rather than silently lose assignments or invent privileges.
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT users.id FROM users
                LEFT JOIN user_roles ON user_roles.user_id = users.id
                GROUP BY users.id HAVING count(user_roles.role_id) <> 1
            ) OR EXISTS (SELECT 1 FROM roles WHERE name NOT IN ('viewer', 'hr')) THEN
                RAISE EXCEPTION 'Cannot downgrade: each user must have exactly one viewer/hr '
                    'role and custom roles must be removed explicitly';
            END IF;
        END $$
        """
    )
    op.add_column("users", sa.Column("role", sa.String(length=20), nullable=True))
    op.execute(
        "UPDATE users SET role = roles.name FROM user_roles "
        "JOIN roles ON roles.id = user_roles.role_id WHERE users.id = user_roles.user_id"
    )
    op.alter_column("users", "role", nullable=False)
    op.create_check_constraint("user_role", "users", "role IN ('viewer', 'hr')")
    op.drop_index("ix_user_roles_role_id", table_name="user_roles")
    op.drop_table("user_roles")
    op.drop_table("roles")
