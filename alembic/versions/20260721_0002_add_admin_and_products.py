"""add admin user fields and products

Revision ID: 20260721_0002
Revises: 20260721_0001
Create Date: 2026-07-21
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260721_0002"
down_revision: str | None = "20260721_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users", sa.Column("name", sa.String(length=100), nullable=False, server_default="")
    )
    op.add_column(
        "users", sa.Column("surname", sa.String(length=100), nullable=False, server_default="")
    )
    op.add_column("users", sa.Column("patronymic", sa.String(length=100), nullable=True))
    op.add_column("users", sa.Column("comment", sa.String(length=2000), nullable=True))
    op.add_column("users", sa.Column("avatar_image", sa.String(length=2048), nullable=True))
    op.add_column("users", sa.Column("header_image", sa.String(length=2048), nullable=True))
    op.add_column("users", sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True))

    op.create_table(
        "products",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.String(length=5000), nullable=True),
        sa.Column("images", sa.JSON(), nullable=True),
        sa.Column("header_image", sa.String(length=2048), nullable=True),
        sa.Column("price", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("ozon_price", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("wb_price", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_products_title"), "products", ["title"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_products_title"), table_name="products")
    op.drop_table("products")
    op.drop_column("users", "created_by")
    op.drop_column("users", "header_image")
    op.drop_column("users", "avatar_image")
    op.drop_column("users", "comment")
    op.drop_column("users", "patronymic")
    op.drop_column("users", "surname")
    op.drop_column("users", "name")
