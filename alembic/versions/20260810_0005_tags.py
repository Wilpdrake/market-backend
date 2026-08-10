"""Add product tags.

Revision ID: 20260810_0005
Revises: 20260810_0004
Create Date: 2026-08-10
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID as PGUUID

from alembic import op

revision: str = "20260810_0005"
down_revision: str | None = "20260810_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "tags",
        sa.Column("id", PGUUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("slug", sa.String(length=100), nullable=False),
        sa.Column("description", sa.String(length=2000), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index("ix_tags_name", "tags", ["name"])
    op.create_index("ix_tags_slug", "tags", ["slug"], unique=True)
    op.create_table(
        "product_tags",
        sa.Column(
            "product_id",
            PGUUID(as_uuid=True),
            sa.ForeignKey("products.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "tag_id",
            PGUUID(as_uuid=True),
            sa.ForeignKey("tags.id", ondelete="CASCADE"),
            primary_key=True,
        ),
    )
    op.create_index("ix_product_tags_tag_id", "product_tags", ["tag_id"])


def downgrade() -> None:
    op.drop_index("ix_product_tags_tag_id", table_name="product_tags")
    op.drop_table("product_tags")
    op.drop_index("ix_tags_slug", table_name="tags")
    op.drop_index("ix_tags_name", table_name="tags")
    op.drop_table("tags")
