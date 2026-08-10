"""Order aggregate.

Prices are authoritative server-side values: the storefront submits product identifiers and
quantities only, and the backend resolves every unit price from the catalog. Amounts are
``Decimal`` because money must never travel through a binary floating point type.
"""

from datetime import UTC, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID, uuid4

from pydantic import Field

from app.models import EntityModel

type OrderStatus = Literal[
    "new",
    "awaiting_payment",
    "paid",
    "payment_failed",
    "cancelled",
    "refunded",
]

type CrmStatus = Literal[
    "payment_verification",
    "assembling",
    "ready_to_ship",
    "in_transit",
    "awaiting_pickup",
    "received",
    "closed",
]

CRM_STATUSES: frozenset[str] = frozenset(
    {
        "payment_verification",
        "assembling",
        "ready_to_ship",
        "in_transit",
        "awaiting_pickup",
        "received",
        "closed",
    }
)

ORDER_CURRENCY = "RUB"

# Statuses in which an order still expects money to arrive. Creating a second payment is only
# allowed while the order sits in one of them.
PAYABLE_ORDER_STATUSES: frozenset[str] = frozenset({"new", "awaiting_payment", "payment_failed"})


class Customer(EntityModel):
    name: str = Field(min_length=1, max_length=200)
    email: str = Field(min_length=3, max_length=320)
    phone: str = Field(min_length=1, max_length=32)


class OrderItem(EntityModel):
    product_id: UUID
    title: str = Field(min_length=1, max_length=255)
    quantity: int = Field(ge=1)
    unit_price: Decimal = Field(ge=0, max_digits=12, decimal_places=2)
    id: UUID = Field(default_factory=uuid4)

    @property
    def total(self) -> Decimal:
        return self.unit_price * self.quantity


class Order(EntityModel):
    user_id: UUID
    customer: Customer
    items: list[OrderItem] = Field(min_length=1)
    id: UUID = Field(default_factory=uuid4)
    status: OrderStatus = "new"
    crm_status: CrmStatus = "payment_verification"
    currency: str = ORDER_CURRENCY
    comment: str | None = Field(default=None, max_length=2000)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @property
    def total(self) -> Decimal:
        return sum((item.total for item in self.items), Decimal("0"))

    @property
    def is_payable(self) -> bool:
        return self.status in PAYABLE_ORDER_STATUSES
