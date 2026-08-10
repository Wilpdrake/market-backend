"""Checkout use cases for the T-Bank acquiring provider.

Three invariants drive this service:

1. **Idempotency.** ``create`` is keyed by ``(order_id, idempotency_key)``. A retried request
   returns the stored payment and never calls ``/v2/Init`` a second time.
2. **Server-side amounts.** The charged amount always comes from the order aggregate.
3. **Convergent state.** Webhooks and polling funnel into ``_apply_provider_state``, so both
   paths produce the same payment and order status regardless of arrival order.
"""

from datetime import UTC, datetime
from uuid import UUID

from app.application.orders.services import OrderService
from app.application.payments.exceptions import PaymentAlreadyExists, PaymentProviderError
from app.application.payments.ports import (
    InitPaymentCommand,
    PaymentGateway,
    PaymentRepository,
    ProviderPayment,
)
from app.application.users.exceptions import ConflictError, NotFoundError
from app.domain.orders.models import Order, OrderStatus
from app.domain.payments.models import (
    ORDER_STATUS_BY_PAYMENT,
    Payment,
    PaymentOption,
    map_provider_status,
)
from app.domain.users.models import User
from app.models import replace_model as replace


class PaymentService:
    def __init__(
        self,
        payments: PaymentRepository,
        orders: OrderService,
        gateway: PaymentGateway,
    ) -> None:
        self.payments = payments
        self.orders = orders
        self.gateway = gateway

    def options(self) -> list[PaymentOption]:
        return [option for option in self.gateway.options() if option.enabled]

    def _option(self, payment_option_id: str) -> PaymentOption:
        option = next(
            (item for item in self.gateway.options() if item.id == payment_option_id),
            None,
        )
        if option is None or not option.enabled:
            raise NotFoundError("Unknown payment option")
        return option

    async def create(
        self,
        order_id: UUID,
        payment_option_id: str,
        idempotency_key: str,
        *,
        actor: User,
    ) -> tuple[Payment, bool]:
        """Return ``(payment, created)``; ``created`` is False for an idempotent replay."""
        order = await self.orders.get_for_actor(order_id, actor=actor)

        existing = await self.payments.get_by_idempotency_key(order_id, idempotency_key)
        if existing is not None:
            return existing, False

        if not order.is_payable:
            raise ConflictError(f"Order in status '{order.status}' cannot be paid")

        active = await self.payments.get_active_for_order(order_id)
        if active is not None and not active.is_terminal:
            raise ConflictError("The order already has an active payment")

        option = self._option(payment_option_id)
        try:
            payment = await self.payments.add(
                Payment(
                    order_id=order.id,
                    payment_option_id=option.id,
                    idempotency_key=idempotency_key,
                    amount=order.total,
                    currency=order.currency,
                )
            )
        except PaymentAlreadyExists as error:
            # A concurrent checkout inserted either this key or another active payment first.
            existing = await self.payments.get_by_idempotency_key(order_id, idempotency_key)
            if existing is not None:
                return existing, False
            raise ConflictError("The order already has an active payment") from error

        try:
            provider = await self.gateway.init_payment(
                InitPaymentCommand(
                    order_id=order.id,
                    payment_id=payment.id,
                    option=option,
                    amount=payment.amount,
                    description=self._description(order),
                    customer_email=order.customer.email,
                    customer_phone=order.customer.phone,
                )
            )
        except PaymentProviderError:
            # Do not strand a locally-created pending payment after provider transport failure.
            await self._store(replace(payment, status="failed"), order=order)
            raise
        payment = await self._apply_provider_state(payment, provider, order=order)
        return payment, True

    async def get_for_order(self, order_id: UUID, *, actor: User) -> Payment:
        order = await self.orders.get_for_actor(order_id, actor=actor)
        payment = await self.payments.get_active_for_order(order_id)
        if payment is None:
            raise NotFoundError("Payment not found")
        # Reconcile with the provider when the webhook has not arrived yet.
        if not payment.is_terminal and payment.provider_payment_id:
            provider = await self.gateway.get_state(payment.provider_payment_id)
            payment = await self._apply_provider_state(payment, provider, order=order)
        return payment

    async def cancel(self, order_id: UUID, *, actor: User) -> Payment:
        order = await self.orders.get_for_actor(order_id, actor=actor)
        payment = await self.payments.get_active_for_order(order_id)
        if payment is None:
            raise NotFoundError("Payment not found")
        if not payment.is_cancellable:
            raise ConflictError(f"Payment in status '{payment.status}' cannot be cancelled")
        if payment.provider_payment_id is None:
            # Never reached the provider, so cancelling locally is authoritative.
            return await self._store(
                replace(payment, status="cancelled", confirmation=None), order=order
            )
        provider = await self.gateway.cancel(payment.provider_payment_id)
        return await self._apply_provider_state(payment, provider, order=order)

    async def handle_notification(self, payload: dict[str, object]) -> bool:
        """Apply a verified provider notification. Returns False when the signature is invalid."""
        if not self.gateway.verify_notification(payload):
            return False

        provider_payment_id = payload.get("PaymentId")
        if provider_payment_id is None:
            return False

        payment = await self.payments.get_by_provider_payment_id(str(provider_payment_id))
        if payment is None:
            # An unknown payment is acknowledged so the provider stops retrying for 30 days.
            return True
        if payment.is_terminal:
            return True

        order = await self.orders.get(payment.order_id)
        await self._apply_provider_state(
            payment,
            ProviderPayment(
                provider_payment_id=str(provider_payment_id),
                status=str(payload.get("Status", "")),
                confirmation=payment.confirmation,
                failure_message=self._notification_error(payload),
            ),
            order=order,
        )
        return True

    async def _apply_provider_state(
        self,
        payment: Payment,
        provider: ProviderPayment,
        *,
        order: Order,
    ) -> Payment:
        status = map_provider_status(provider.status)
        return await self._store(
            replace(
                payment,
                provider_payment_id=provider.provider_payment_id or payment.provider_payment_id,
                status=status,
                confirmation=provider.confirmation or payment.confirmation,
                failure_message=provider.failure_message,
            ),
            order=order,
        )

    async def _store(self, payment: Payment, *, order: Order) -> Payment:
        saved = await self.payments.save(replace(payment, updated_at=datetime.now(UTC)))
        order_status: OrderStatus = ORDER_STATUS_BY_PAYMENT[saved.status]  # type: ignore[assignment]
        await self.orders.set_status(order, order_status)
        return saved

    @staticmethod
    def _description(order: Order) -> str:
        # T-Bank truncates the payment form description at 140 characters for SBP.
        return f"Заказ {str(order.id)[:8]}"[:140]

    @staticmethod
    def _notification_error(payload: dict[str, object]) -> str | None:
        code = str(payload.get("ErrorCode", "0") or "0")
        if code == "0":
            return None
        message = payload.get("Message") or payload.get("Details") or "Payment failed"
        return str(message)[:1000]
