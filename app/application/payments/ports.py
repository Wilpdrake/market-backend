"""Ports for the payment provider boundary.

``PaymentGateway`` is deliberately narrow: the application layer never learns about
``TerminalKey``, request signing or HTTP. Swapping T-Bank for another acquirer only requires a
new adapter in ``app/infrastructure``.
"""

from decimal import Decimal
from typing import Protocol
from uuid import UUID

from pydantic import Field

from app.domain.payments.models import Payment, PaymentConfirmation, PaymentOption
from app.models import CommandModel, EntityModel


class ProviderPayment(EntityModel):
    """Normalized provider response, already translated out of T-Bank vocabulary."""

    provider_payment_id: str
    status: str
    confirmation: PaymentConfirmation | None = None
    failure_message: str | None = None


class InitPaymentCommand(CommandModel):
    order_id: UUID
    payment_id: UUID
    option: PaymentOption
    amount: Decimal = Field(ge=0)
    description: str = Field(max_length=140)
    customer_email: str
    customer_phone: str


class PaymentGateway(Protocol):
    """Provider-facing operations required by the checkout flow."""

    def options(self) -> list[PaymentOption]: ...

    async def init_payment(self, command: InitPaymentCommand) -> ProviderPayment: ...

    async def get_state(self, provider_payment_id: str) -> ProviderPayment: ...

    async def cancel(self, provider_payment_id: str) -> ProviderPayment: ...

    def verify_notification(self, payload: dict[str, object]) -> bool: ...


class PaymentRepository(Protocol):
    async def add(self, payment: Payment) -> Payment: ...

    async def get_by_id(self, payment_id: UUID) -> Payment | None: ...

    async def get_by_idempotency_key(self, order_id: UUID, key: str) -> Payment | None: ...

    async def get_active_for_order(self, order_id: UUID) -> Payment | None: ...

    async def get_by_provider_payment_id(self, provider_payment_id: str) -> Payment | None: ...

    async def save(self, payment: Payment) -> Payment: ...
