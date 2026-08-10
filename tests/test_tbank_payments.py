"""T-Bank acquiring adapter and checkout service behaviour."""

from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from app.application.orders.models import CreateOrder, CreateOrderCustomer, CreateOrderItem
from app.application.orders.services import OrderService
from app.application.payments.exceptions import PaymentProviderError
from app.application.payments.ports import InitPaymentCommand, ProviderPayment
from app.application.payments.services import PaymentService
from app.application.users.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from app.domain.orders.models import Order
from app.domain.payments.models import Payment, PaymentConfirmation, PaymentOption
from app.domain.products.models import Product
from app.domain.users.models import User
from app.infrastructure.payments.tbank import (
    StubPaymentGateway,
    TBankPaymentGateway,
    default_payment_options,
    sign,
    to_kopecks,
)

ADMIN_ID = UUID("00000000-0000-0000-0000-0000000000ad")
USER_ID = UUID("00000000-0000-0000-0000-000000000001")
OTHER_USER_ID = UUID("00000000-0000-0000-0000-000000000002")


def make_user(user_id: UUID = USER_ID, *, is_superuser: bool = False) -> User:
    return User(
        id=user_id,
        email=f"{user_id}@example.com",
        password_hash="hash",
        is_superuser=is_superuser,
    )


class InMemoryProductRepository:
    def __init__(self, products: list[Product] | None = None) -> None:
        self.products = {product.id: product for product in products or []}

    async def add(self, product: Product) -> Product:
        self.products[product.id] = product
        return product

    async def get_by_id(self, product_id: UUID) -> Product | None:
        return self.products.get(product_id)

    async def list(self, *, offset: int, limit: int) -> list[Product]:
        return list(self.products.values())[offset : offset + limit]

    async def save(self, product: Product) -> Product:
        self.products[product.id] = product
        return product

    async def delete(self, product_id: UUID) -> None:
        self.products.pop(product_id, None)


class InMemoryOrderRepository:
    def __init__(self) -> None:
        self.orders: dict[UUID, Order] = {}

    async def add(self, order: Order) -> Order:
        self.orders[order.id] = order
        return order

    async def get_by_id(self, order_id: UUID) -> Order | None:
        return self.orders.get(order_id)

    async def list_for_user(self, user_id: UUID, *, offset: int, limit: int) -> list[Order]:
        owned = [order for order in self.orders.values() if order.user_id == user_id]
        return owned[offset : offset + limit]

    async def save(self, order: Order) -> Order:
        self.orders[order.id] = order
        return order


class InMemoryPaymentRepository:
    def __init__(self) -> None:
        self.payments: dict[UUID, Payment] = {}

    async def add(self, payment: Payment) -> Payment:
        self.payments[payment.id] = payment
        return payment

    async def get_by_id(self, payment_id: UUID) -> Payment | None:
        return self.payments.get(payment_id)

    async def get_by_idempotency_key(self, order_id: UUID, key: str) -> Payment | None:
        return next(
            (
                payment
                for payment in self.payments.values()
                if payment.order_id == order_id and payment.idempotency_key == key
            ),
            None,
        )

    async def get_active_for_order(self, order_id: UUID) -> Payment | None:
        owned = [payment for payment in self.payments.values() if payment.order_id == order_id]
        return max(owned, key=lambda payment: payment.created_at) if owned else None

    async def get_by_provider_payment_id(self, provider_payment_id: str) -> Payment | None:
        return next(
            (
                payment
                for payment in self.payments.values()
                if payment.provider_payment_id == provider_payment_id
            ),
            None,
        )

    async def save(self, payment: Payment) -> Payment:
        self.payments[payment.id] = payment
        return payment


class RecordingGateway(StubPaymentGateway):
    """Stub gateway that counts Init calls so idempotency can be asserted."""

    def __init__(self) -> None:
        super().__init__(default_payment_options())
        self.init_calls = 0

    async def init_payment(self, command: InitPaymentCommand) -> ProviderPayment:
        self.init_calls += 1
        return await super().init_payment(command)


async def build_checkout(
    price: str = "2500.00",
) -> tuple[PaymentService, OrderService, Product, RecordingGateway]:
    product = Product(
        title="Хохломская тарелка",
        price=Decimal(price),
        created_by=ADMIN_ID,
        updated_by=ADMIN_ID,
    )
    orders = OrderService(InMemoryOrderRepository(), InMemoryProductRepository([product]))
    gateway = RecordingGateway()
    payments = PaymentService(InMemoryPaymentRepository(), orders, gateway)
    return payments, orders, product, gateway


def order_command(product: Product, quantity: int = 2) -> CreateOrder:
    return CreateOrder(
        items=(CreateOrderItem(product_id=product.id, quantity=quantity),),
        customer=CreateOrderCustomer(
            name="Иван Иванов",
            email="ivan@example.com",
            phone="+79990000000",
        ),
    )


# --- signature -------------------------------------------------------------------------------


def test_token_matches_the_documented_tbank_example() -> None:
    """Official vector from https://developer.tbank.ru/eacq/intro/developer/token.

    Nested ``DATA``/``Receipt`` objects are excluded from the signature, which is exactly what
    the documented hash encodes — keeping this test honest about the protocol, not just about
    our own implementation.
    """
    payload = {
        "TerminalKey": "MerchantTerminalKey",
        "Amount": 19200,
        "OrderId": "00000",
        "Description": "Подарочная карта на 1000 рублей",
        "DATA": {"Phone": "+71234567890", "Email": "a@test.com"},
        "Receipt": {"Email": "a@test.ru", "Items": []},
    }

    assert (
        sign(payload, "11111111111111")
        == "72dd466f8ace0a37a1f740ce5fb78101712bc0665d91a8108c7c8a0ccd426db2"
    )


def test_token_ignores_nested_objects_and_lowercases_booleans() -> None:
    flat = sign({"TerminalKey": "t", "Amount": 100, "Recurrent": True}, "secret")
    nested = sign(
        {
            "TerminalKey": "t",
            "Amount": 100,
            "Recurrent": True,
            "DATA": {"Email": "a@b.c"},
            "Receipt": {"Items": []},
            "Token": "stale",
        },
        "secret",
    )

    assert flat == nested


def test_amounts_convert_to_kopecks() -> None:
    assert to_kopecks(Decimal("2500.00")) == 250000
    assert to_kopecks(Decimal("3.12")) == 312


def test_notification_signature_is_verified() -> None:
    gateway = TBankPaymentGateway(
        terminal_key="TinkoffBankTest",
        password="TinkoffBankTest",
        options=default_payment_options(),
    )
    payload: dict[str, object] = {
        "TerminalKey": "TinkoffBankTest",
        "OrderId": "21050",
        "Success": True,
        "Status": "CONFIRMED",
        "PaymentId": 8742591,
        "Amount": 9855,
    }
    payload["Token"] = sign(dict(payload), "TinkoffBankTest")

    assert gateway.verify_notification(payload) is True

    assert gateway.verify_notification({**payload, "Amount": 1}) is False
    assert gateway.verify_notification({**payload, "Token": ""}) is False
    assert gateway.verify_notification({k: v for k, v in payload.items() if k != "Token"}) is False


def test_notification_from_a_foreign_terminal_is_rejected() -> None:
    gateway = TBankPaymentGateway(
        terminal_key="OurTerminal",
        password="secret",
        options=default_payment_options(),
    )
    payload: dict[str, object] = {
        "TerminalKey": "SomeoneElse",
        "PaymentId": 1,
        "Status": "CONFIRMED",
    }
    payload["Token"] = sign(dict(payload), "secret")

    assert gateway.verify_notification(payload) is False


def test_init_response_without_payment_id_raises_provider_error() -> None:
    gateway = TBankPaymentGateway(terminal_key="t", password="p", options=default_payment_options())

    with pytest.raises(PaymentProviderError):
        gateway._to_provider_payment({"Success": False, "ErrorCode": "204", "Message": "Отказ"})


def test_sbp_option_produces_a_qr_confirmation() -> None:
    gateway = TBankPaymentGateway(terminal_key="t", password="p", options=default_payment_options())
    sbp = next(option for option in default_payment_options() if option.kind == "sbp")
    card = next(option for option in default_payment_options() if option.kind == "card")

    body = {"PaymentURL": "https://securepay.tinkoff.ru/abc"}

    assert gateway._confirmation(body, sbp) == PaymentConfirmation(
        type="qr", url="https://securepay.tinkoff.ru/abc"
    )
    assert gateway._confirmation(body, card).type == "redirect"
    assert gateway._confirmation({}, card) is None


# --- checkout flow ---------------------------------------------------------------------------


async def test_order_total_is_resolved_from_the_catalog() -> None:
    payments, orders, product, _ = await build_checkout(price="2500.00")

    order = await orders.create(order_command(product, quantity=2), actor=make_user())

    assert order.total == Decimal("5000.00")
    assert order.items[0].unit_price == Decimal("2500.00")
    assert order.status == "new"


async def test_payment_creation_is_idempotent_per_key() -> None:
    payments, orders, product, gateway = await build_checkout()
    order = await orders.create(order_command(product), actor=make_user())
    actor = make_user()

    first, created_first = await payments.create(order.id, "tbank-card", "key-1", actor=actor)
    second, created_second = await payments.create(order.id, "tbank-card", "key-1", actor=actor)

    assert created_first is True
    assert created_second is False
    assert first.id == second.id
    assert gateway.init_calls == 1


async def test_payment_marks_the_order_awaiting_payment() -> None:
    payments, orders, product, _ = await build_checkout()
    order = await orders.create(order_command(product), actor=make_user())

    payment, _ = await payments.create(order.id, "tbank-card", "key-1", actor=make_user())

    assert payment.status == "pending"
    assert payment.confirmation is not None
    assert payment.amount == order.total
    assert (await orders.get(order.id)).status == "awaiting_payment"


async def test_second_active_payment_is_rejected() -> None:
    payments, orders, product, _ = await build_checkout()
    order = await orders.create(order_command(product), actor=make_user())
    actor = make_user()
    await payments.create(order.id, "tbank-card", "key-1", actor=actor)

    with pytest.raises(ConflictError):
        await payments.create(order.id, "tbank-card", "key-2", actor=actor)


async def test_unknown_payment_option_is_rejected() -> None:
    payments, orders, product, _ = await build_checkout()
    order = await orders.create(order_command(product), actor=make_user())

    with pytest.raises(NotFoundError):
        await payments.create(order.id, "paypal", "key-1", actor=make_user())


async def test_a_foreign_order_cannot_be_paid() -> None:
    payments, orders, product, _ = await build_checkout()
    order = await orders.create(order_command(product), actor=make_user())

    with pytest.raises(PermissionDeniedError):
        await payments.create(order.id, "tbank-card", "key-1", actor=make_user(OTHER_USER_ID))


async def test_administrator_may_read_a_foreign_order() -> None:
    _, orders, product, _ = await build_checkout()
    order = await orders.create(order_command(product), actor=make_user())

    found = await orders.get_for_actor(order.id, actor=make_user(OTHER_USER_ID, is_superuser=True))

    assert found.id == order.id


async def test_polling_settles_the_payment_and_the_order() -> None:
    payments, orders, product, _ = await build_checkout()
    order = await orders.create(order_command(product), actor=make_user())
    actor = make_user()
    await payments.create(order.id, "tbank-card", "key-1", actor=actor)

    settled = await payments.get_for_order(order.id, actor=actor)

    assert settled.status == "succeeded"
    assert (await orders.get(order.id)).status == "paid"


async def test_paid_order_cannot_be_paid_again() -> None:
    payments, orders, product, _ = await build_checkout()
    order = await orders.create(order_command(product), actor=make_user())
    actor = make_user()
    await payments.create(order.id, "tbank-card", "key-1", actor=actor)
    await payments.get_for_order(order.id, actor=actor)

    with pytest.raises(ConflictError):
        await payments.create(order.id, "tbank-card", "key-2", actor=actor)


async def test_cancelling_a_payment_cancels_the_order() -> None:
    payments, orders, product, _ = await build_checkout()
    order = await orders.create(order_command(product), actor=make_user())
    actor = make_user()
    await payments.create(order.id, "tbank-card", "key-1", actor=actor)

    cancelled = await payments.cancel(order.id, actor=actor)

    assert cancelled.status == "cancelled"
    assert (await orders.get(order.id)).status == "cancelled"


async def test_webhook_confirms_the_payment() -> None:
    payments, orders, product, _ = await build_checkout()
    order = await orders.create(order_command(product), actor=make_user())
    payment, _ = await payments.create(order.id, "tbank-card", "key-1", actor=make_user())

    accepted = await payments.handle_notification(
        {"PaymentId": payment.provider_payment_id, "Status": "CONFIRMED", "Success": True}
    )

    assert accepted is True
    assert (await orders.get(order.id)).status == "paid"


async def test_webhook_records_a_rejection_reason() -> None:
    payments, orders, product, _ = await build_checkout()
    order = await orders.create(order_command(product), actor=make_user())
    payment, _ = await payments.create(order.id, "tbank-card", "key-1", actor=make_user())

    await payments.handle_notification(
        {
            "PaymentId": payment.provider_payment_id,
            "Status": "REJECTED",
            "Success": False,
            "ErrorCode": "1051",
            "Message": "Недостаточно средств",
        }
    )
    stored = await payments.payments.get_by_id(payment.id)

    assert stored is not None
    assert stored.status == "failed"
    assert stored.failure_message == "Недостаточно средств"
    assert (await orders.get(order.id)).status == "payment_failed"


async def test_webhook_for_an_unknown_payment_is_acknowledged() -> None:
    payments, _, _, _ = await build_checkout()

    assert await payments.handle_notification({"PaymentId": "404", "Status": "CONFIRMED"}) is True


async def test_webhook_without_payment_id_is_rejected() -> None:
    payments, _, _, _ = await build_checkout()

    assert await payments.handle_notification({"Status": "CONFIRMED"}) is False


async def test_terminal_payment_ignores_late_notifications() -> None:
    payments, orders, product, _ = await build_checkout()
    order = await orders.create(order_command(product), actor=make_user())
    payment, _ = await payments.create(order.id, "tbank-card", "key-1", actor=make_user())
    await payments.handle_notification(
        {"PaymentId": payment.provider_payment_id, "Status": "CONFIRMED", "Success": True}
    )

    await payments.handle_notification(
        {"PaymentId": payment.provider_payment_id, "Status": "REJECTED", "Success": False}
    )
    stored = await payments.payments.get_by_id(payment.id)

    assert stored is not None
    assert stored.status == "succeeded"
    assert (await orders.get(order.id)).status == "paid"


async def test_product_without_a_price_cannot_be_ordered() -> None:
    product = Product(title="Витрина", price=None, created_by=ADMIN_ID, updated_by=ADMIN_ID)
    orders = OrderService(InMemoryOrderRepository(), InMemoryProductRepository([product]))

    with pytest.raises(ConflictError):
        await orders.create(order_command(product), actor=make_user())


async def test_missing_product_is_reported() -> None:
    orders = OrderService(InMemoryOrderRepository(), InMemoryProductRepository([]))
    command = CreateOrder(
        items=(CreateOrderItem(product_id=uuid4(), quantity=1),),
        customer=CreateOrderCustomer(name="И", email="i@e.com", phone="+70000000000"),
    )

    with pytest.raises(NotFoundError):
        await orders.create(command, actor=make_user())


def test_only_enabled_options_are_public() -> None:
    gateway = StubPaymentGateway(
        [
            PaymentOption(id="on", title="On", kind="card", enabled=True),
            PaymentOption(id="off", title="Off", kind="sbp", enabled=False),
        ]
    )
    service = PaymentService(InMemoryPaymentRepository(), None, gateway)  # type: ignore[arg-type]

    assert [option.id for option in service.options()] == ["on"]
