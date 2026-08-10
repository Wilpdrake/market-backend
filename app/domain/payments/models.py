"""Payment aggregate for the T-Bank (Тинькофф) acquiring provider.

One order has at most one *active* payment. A payment is identified locally by ``id`` and
remotely by ``provider_payment_id`` (T-Bank ``PaymentId``). ``idempotency_key`` belongs to a
single frontend checkout attempt: retrying the same key must return the stored payment instead
of calling ``/v2/Init`` again.
"""

from datetime import UTC, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID, uuid4

from pydantic import Field

from app.models import EntityModel

type PaymentStatus = Literal[
    "pending",
    "authorized",
    "succeeded",
    "failed",
    "cancelled",
    "refunded",
]

type PaymentKind = Literal["card", "sbp"]
type ConfirmationType = Literal["redirect", "qr"]

PAYMENT_PROVIDER = "tbank"

# Terminal states never change again, so reconciliation and webhooks may skip them entirely.
TERMINAL_PAYMENT_STATUSES: frozenset[str] = frozenset(
    {"succeeded", "failed", "cancelled", "refunded"}
)

# T-Bank payment states mapped onto our storefront vocabulary. Unknown provider states are
# treated as ``pending`` so an unexpected value never silently marks an order as paid.
TBANK_STATUS_MAP: dict[str, PaymentStatus] = {
    "NEW": "pending",
    "FORM_SHOWED": "pending",
    "AUTHORIZING": "pending",
    "3DS_CHECKING": "pending",
    "3DS_CHECKED": "pending",
    "PAY_CHECKING": "pending",
    "AUTHORIZED": "authorized",
    "CONFIRMING": "authorized",
    "CONFIRMED": "succeeded",
    "REVERSING": "cancelled",
    "PARTIAL_REVERSED": "cancelled",
    "REVERSED": "cancelled",
    "REFUNDING": "refunded",
    "PARTIAL_REFUNDED": "refunded",
    "REFUNDED": "refunded",
    "CANCELED": "cancelled",
    "DEADLINE_EXPIRED": "failed",
    "ATTEMPTS_EXPIRED": "failed",
    "REJECTED": "failed",
    "AUTH_FAIL": "failed",
}

# Order status implied by each payment status; the order is the customer-facing aggregate.
ORDER_STATUS_BY_PAYMENT: dict[PaymentStatus, str] = {
    "pending": "awaiting_payment",
    "authorized": "awaiting_payment",
    "succeeded": "paid",
    "failed": "payment_failed",
    "cancelled": "cancelled",
    "refunded": "refunded",
}


def map_provider_status(provider_status: str) -> PaymentStatus:
    return TBANK_STATUS_MAP.get(provider_status.upper(), "pending")


class PaymentConfirmation(EntityModel):
    type: ConfirmationType
    url: str = Field(min_length=1, max_length=2048)


class PaymentOption(EntityModel):
    """Public payment method. ``id`` is a stable slug and never a T-Bank ``TerminalKey``."""

    id: str = Field(min_length=1, max_length=64)
    title: str = Field(min_length=1, max_length=128)
    kind: PaymentKind
    enabled: bool = True


class Payment(EntityModel):
    order_id: UUID
    payment_option_id: str = Field(min_length=1, max_length=64)
    idempotency_key: str = Field(min_length=1, max_length=64)
    amount: Decimal = Field(ge=0, max_digits=12, decimal_places=2)
    id: UUID = Field(default_factory=uuid4)
    provider: str = PAYMENT_PROVIDER
    provider_payment_id: str | None = Field(default=None, max_length=64)
    status: PaymentStatus = "pending"
    currency: str = "RUB"
    confirmation: PaymentConfirmation | None = None
    failure_message: str | None = Field(default=None, max_length=1000)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @property
    def is_terminal(self) -> bool:
        return self.status in TERMINAL_PAYMENT_STATUSES

    @property
    def is_cancellable(self) -> bool:
        return self.status in {"pending", "authorized"}
