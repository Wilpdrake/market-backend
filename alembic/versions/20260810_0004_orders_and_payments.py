"""Create checkout orders and T-Bank payments.

Revision ID: 20260810_0004
Revises: 20260802_0003
Create Date: 2026-08-10
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID as PGUUID

from alembic import op

revision: str = "20260810_0004"
down_revision: str | None = "20260802_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_ORDER_STATUSES = "'new', 'awaiting_payment', 'paid', 'payment_failed', 'cancelled', 'refunded'"
_PAYMENT_STATUSES = "'pending', 'authorized', 'succeeded', 'failed', 'cancelled', 'refunded'"


def upgrade() -> None:
    op.create_table(
        "orders",
        sa.Column("id", PGUUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            PGUUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="new"),
        sa.Column("currency", sa.String(length=3), nullable=False, server_default="RUB"),
        sa.Column("customer_name", sa.String(length=200), nullable=False),
        sa.Column("customer_email", sa.String(length=320), nullable=False),
        sa.Column("customer_phone", sa.String(length=32), nullable=False),
        sa.Column("comment", sa.String(length=2000), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(f"status IN ({_ORDER_STATUSES})", name="ck_orders_status"),
    )
    op.create_index("ix_orders_user_id", "orders", ["user_id"])
    op.create_index("ix_orders_status", "orders", ["status"])

    # Line items snapshot title and unit price: later catalog edits must not rewrite an order.
    op.create_table(
        "order_items",
        sa.Column("id", PGUUID(as_uuid=True), primary_key=True),
        sa.Column(
            "order_id",
            PGUUID(as_uuid=True),
            sa.ForeignKey("orders.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "product_id",
            PGUUID(as_uuid=True),
            sa.ForeignKey("products.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("unit_price", sa.Numeric(12, 2), nullable=False),
        sa.CheckConstraint("quantity > 0", name="ck_order_items_quantity_positive"),
        sa.CheckConstraint("unit_price >= 0", name="ck_order_items_unit_price_non_negative"),
    )
    op.create_index("ix_order_items_order_id", "order_items", ["order_id"])

    op.create_table(
        "payments",
        sa.Column("id", PGUUID(as_uuid=True), primary_key=True),
        sa.Column(
            "order_id",
            PGUUID(as_uuid=True),
            sa.ForeignKey("orders.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("provider", sa.String(length=32), nullable=False, server_default="tbank"),
        sa.Column("provider_payment_id", sa.String(length=64), nullable=True),
        sa.Column("payment_option_id", sa.String(length=64), nullable=False),
        sa.Column("idempotency_key", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False, server_default="RUB"),
        sa.Column("confirmation_type", sa.String(length=16), nullable=True),
        sa.Column("confirmation_url", sa.String(length=2048), nullable=True),
        sa.Column("failure_message", sa.String(length=1000), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(f"status IN ({_PAYMENT_STATUSES})", name="ck_payments_status"),
        # Checkout idempotency is enforced by the database, so a retried request cannot create
        # a second provider payment even when two requests race.
        sa.UniqueConstraint("order_id", "idempotency_key", name="uq_payments_order_idempotency"),
    )
    op.create_index("ix_payments_order_id", "payments", ["order_id"])
    # At most one payment can be pending/authorized for an order, even across API workers.
    op.create_index(
        "uq_payments_active_order",
        "payments",
        ["order_id"],
        unique=True,
        postgresql_where=sa.text("status IN ('pending', 'authorized')"),
    )
    op.create_index("ix_payments_status", "payments", ["status"])
    op.create_index(
        "ix_payments_provider_payment_id", "payments", ["provider_payment_id"], unique=True
    )


def downgrade() -> None:
    op.drop_index("ix_payments_provider_payment_id", table_name="payments")
    op.drop_index("ix_payments_status", table_name="payments")
    op.drop_index("uq_payments_active_order", table_name="payments")
    op.drop_index("ix_payments_order_id", table_name="payments")
    op.drop_table("payments")
    op.drop_index("ix_order_items_order_id", table_name="order_items")
    op.drop_table("order_items")
    op.drop_index("ix_orders_status", table_name="orders")
    op.drop_index("ix_orders_user_id", table_name="orders")
    op.drop_table("orders")
