"""Persist usernames and explicit administration roles.

Revision ID: 20260802_0003
Revises: 20260721_0002
Create Date: 2026-08-02
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260802_0003"
down_revision: str | None = "20260721_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_ALLOWED_ROLES = "'user', 'moder', 'admin', 'developer', 'owner'"


def upgrade() -> None:
    # ``username`` is nullable because older customer accounts only have an email address.
    op.add_column("users", sa.Column("username", sa.String(length=64), nullable=True))
    op.create_index("ix_users_username", "users", ["username"], unique=True)
    # Keeping ``@`` email-only makes the two login identifier sets disjoint even under
    # concurrent writes, while each column's unique index handles duplicates within its set.
    op.create_check_constraint(
        "ck_users_username_format",
        "users",
        "username IS NULL OR username ~ '^[a-z0-9._+-]+$'",
    )

    op.add_column(
        "users",
        sa.Column("role", sa.String(length=32), nullable=False, server_default="user"),
    )
    # Preserve the old boolean privilege flag when upgrading an existing installation.
    op.execute("UPDATE users SET role = 'admin' WHERE is_superuser IS TRUE")
    op.create_check_constraint("ck_users_role", "users", f"role IN ({_ALLOWED_ROLES})")
    op.create_index("ix_users_role", "users", ["role"], unique=False)
    # Retain the default for compatibility with the previous application during rollout or
    # rollback. New code supplies role explicitly; old code can continue inserting users.


def downgrade() -> None:
    op.drop_index("ix_users_role", table_name="users")
    op.drop_constraint("ck_users_role", "users", type_="check")
    op.drop_column("users", "role")
    op.drop_constraint("ck_users_username_format", "users", type_="check")
    op.drop_index("ix_users_username", table_name="users")
    op.drop_column("users", "username")
