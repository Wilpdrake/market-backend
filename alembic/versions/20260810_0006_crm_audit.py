"""Add CRM status, audit log, and audit setting.

Revision ID: 20260810_0006
Revises: 20260810_0005
Create Date: 2026-08-10
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID as PGUUID

from alembic import op

revision: str = "20260810_0006"
down_revision: str | None = "20260810_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_CRM_STATUSES = (
    "'payment_verification', 'assembling', 'ready_to_ship', 'in_transit', "
    "'awaiting_pickup', 'received', 'closed'"
)


def upgrade() -> None:
    op.add_column(
        "orders",
        sa.Column(
            "crm_status",
            sa.String(length=32),
            nullable=False,
            server_default="payment_verification",
        ),
    )
    op.create_check_constraint("ck_orders_crm_status", "orders", f"crm_status IN ({_CRM_STATUSES})")
    op.create_index("ix_orders_crm_status", "orders", ["crm_status"])

    op.create_table(
        "admin_settings",
        sa.Column("key", sa.String(length=100), primary_key=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_table(
        "audit_log",
        sa.Column("id", PGUUID(as_uuid=True), primary_key=True),
        sa.Column(
            "admin_id",
            PGUUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("admin_name", sa.String(length=201), nullable=False),
        sa.Column("admin_email", sa.String(length=320), nullable=False),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("entity_type", sa.String(length=100), nullable=False),
        sa.Column("entity_id", sa.String(length=100), nullable=True),
        sa.Column("details", sa.String(length=2000), nullable=True),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index("ix_audit_log_admin_id", "audit_log", ["admin_id"])
    op.create_index("ix_audit_log_action", "audit_log", ["action"])
    op.create_index("ix_audit_log_entity_type", "audit_log", ["entity_type"])
    op.create_index("ix_audit_log_created_at", "audit_log", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_audit_log_created_at", table_name="audit_log")
    op.drop_index("ix_audit_log_entity_type", table_name="audit_log")
    op.drop_index("ix_audit_log_action", table_name="audit_log")
    op.drop_index("ix_audit_log_admin_id", table_name="audit_log")
    op.drop_table("audit_log")
    op.drop_table("admin_settings")
    op.drop_index("ix_orders_crm_status", table_name="orders")
    op.drop_constraint("ck_orders_crm_status", "orders", type_="check")
    op.drop_column("orders", "crm_status")
