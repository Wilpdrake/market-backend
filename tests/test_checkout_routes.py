"""End-to-end checkout over HTTP with a real ASGI client.

Unlike the service-level tests these exercise routing, dependency wiring, status codes and the
webhook body contract, using in-memory repositories injected through the dishka container.
"""

from decimal import Decimal
from uuid import UUID

import pytest
from dishka import Provider, Scope, make_async_container, provide
from dishka.integrations.fastapi import setup_dishka
from fastapi.testclient import TestClient

from app.application.orders.ports import OrderRepository
from app.application.orders.services import OrderService
from app.application.payments.ports import PaymentGateway, PaymentRepository
from app.application.payments.services import PaymentService
from app.application.products.ports import ProductRepository
from app.application.products.services import ProductService
from app.application.users.exceptions import InvalidCredentialsError
from app.application.users.services import AuthService
from app.domain.products.models import Product
from app.domain.users.models import User
from app.infrastructure.payments.tbank import StubPaymentGateway, default_payment_options
from app.main import create_app
from tests.test_tbank_payments import (
    ADMIN_ID,
    USER_ID,
    InMemoryOrderRepository,
    InMemoryPaymentRepository,
    InMemoryProductRepository,
    make_user,
)

TOKEN = "test-token"


class FakeAuthService:
    """Minimal AuthService stand-in: one bearer token maps to one user."""

    def __init__(self, user: User) -> None:
        self.user = user

    async def get_current_user(self, token: str) -> User:
        if token != TOKEN:
            raise InvalidCredentialsError("Invalid token")
        return self.user


@pytest.fixture
def product() -> Product:
    return Product(
        title="Хохломская тарелка",
        price=Decimal("2500.00"),
        created_by=ADMIN_ID,
        updated_by=ADMIN_ID,
    )


@pytest.fixture
def client(product: Product) -> TestClient:
    orders = InMemoryOrderRepository()
    payments = InMemoryPaymentRepository()
    products = InMemoryProductRepository([product])
    gateway = StubPaymentGateway(default_payment_options())
    user = make_user()

    class TestProvider(Provider):
        @provide(scope=Scope.APP, provides=OrderRepository)
        def order_repository(self) -> InMemoryOrderRepository:
            return orders

        @provide(scope=Scope.APP, provides=PaymentRepository)
        def payment_repository(self) -> InMemoryPaymentRepository:
            return payments

        @provide(scope=Scope.APP, provides=ProductRepository)
        def product_repository(self) -> InMemoryProductRepository:
            return products

        @provide(scope=Scope.APP, provides=PaymentGateway)
        def payment_gateway(self) -> StubPaymentGateway:
            return gateway

        @provide(scope=Scope.APP, provides=AuthService)
        def auth_service(self) -> FakeAuthService:  # type: ignore[override]
            return FakeAuthService(user)

        order_service = provide(OrderService, scope=Scope.REQUEST)
        payment_service = provide(PaymentService, scope=Scope.REQUEST)

        @provide(scope=Scope.REQUEST)
        def product_service(self, repository: ProductRepository) -> ProductService:
            return ProductService(repository)

    app = create_app()
    setup_dishka(make_async_container(TestProvider()), app)
    return TestClient(app)


def auth() -> dict[str, str]:
    return {"Authorization": f"Bearer {TOKEN}"}


def create_order(client: TestClient, product: Product, quantity: int = 2) -> dict:
    response = client.post(
        "/api/v1/orders",
        headers=auth(),
        json={
            "items": [{"product_id": str(product.id), "quantity": quantity}],
            "customer": {
                "name": "Иван Иванов",
                "email": "ivan@example.com",
                "phone": "+79990000000",
            },
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_payment_options_are_public(client: TestClient) -> None:
    response = client.get("/api/v1/payments/tbank/options")

    assert response.status_code == 200
    body = response.json()
    assert {option["id"] for option in body} == {"tbank-card", "tbank-sbp"}
    # A terminal key must never leak into a public response.
    assert "TerminalKey" not in response.text


def test_order_requires_authentication(client: TestClient, product: Product) -> None:
    response = client.post(
        "/api/v1/orders",
        json={
            "items": [{"product_id": str(product.id), "quantity": 1}],
            "customer": {"name": "И", "email": "i@e.com", "phone": "+70000000000"},
        },
    )

    assert response.status_code == 401


def test_order_total_is_computed_server_side(client: TestClient, product: Product) -> None:
    order = create_order(client, product, quantity=3)

    assert order["total"] == "7500.00"
    assert order["items"][0]["unit_price"] == "2500.00"
    assert order["status"] == "new"


def test_full_checkout_flow(client: TestClient, product: Product) -> None:
    order = create_order(client, product)

    created = client.post(
        f"/api/v1/orders/{order['id']}/payments/tbank",
        headers=auth(),
        json={"payment_option_id": "tbank-card", "idempotency_key": "checkout-1"},
    )
    assert created.status_code == 201, created.text
    payment = created.json()
    assert payment["status"] == "pending"
    assert payment["amount"] == "5000.00"
    assert payment["confirmation"]["type"] == "redirect"
    assert payment["confirmation"]["url"]

    # Replaying the same idempotency key must not start a second payment.
    replay = client.post(
        f"/api/v1/orders/{order['id']}/payments/tbank",
        headers=auth(),
        json={"payment_option_id": "tbank-card", "idempotency_key": "checkout-1"},
    )
    assert replay.status_code == 200
    assert replay.json()["id"] == payment["id"]

    settled = client.get(f"/api/v1/orders/{order['id']}/payment", headers=auth())
    assert settled.status_code == 200
    assert settled.json()["status"] == "succeeded"

    assert client.get(f"/api/v1/orders/{order['id']}", headers=auth()).json()["status"] == "paid"


def test_webhook_answers_with_a_plain_ok_body(client: TestClient, product: Product) -> None:
    order = create_order(client, product)
    payment = client.post(
        f"/api/v1/orders/{order['id']}/payments/tbank",
        headers=auth(),
        json={"payment_option_id": "tbank-sbp", "idempotency_key": "checkout-1"},
    ).json()

    response = client.post(
        "/api/v1/payments/tbank/webhook",
        json={
            "TerminalKey": "test",
            "PaymentId": payment["id"] and payment["confirmation"]["url"].rsplit("/", 1)[-1],
            "Status": "CONFIRMED",
            "Success": True,
        },
    )

    # T-Bank keeps retrying for a month unless the body is exactly "OK".
    assert response.status_code == 200
    assert response.text == "OK"
    assert client.get(f"/api/v1/orders/{order['id']}", headers=auth()).json()["status"] == "paid"


def test_webhook_rejects_an_unsigned_payload(client: TestClient) -> None:
    response = client.post("/api/v1/payments/tbank/webhook", json={"Status": "CONFIRMED"})

    assert response.status_code == 401
    assert response.text != "OK"


def test_sbp_option_returns_a_qr_confirmation(client: TestClient, product: Product) -> None:
    order = create_order(client, product)

    payment = client.post(
        f"/api/v1/orders/{order['id']}/payments/tbank",
        headers=auth(),
        json={"payment_option_id": "tbank-sbp", "idempotency_key": "sbp-1"},
    ).json()

    assert payment["confirmation"]["type"] == "qr"


def test_unknown_option_is_a_404(client: TestClient, product: Product) -> None:
    order = create_order(client, product)

    response = client.post(
        f"/api/v1/orders/{order['id']}/payments/tbank",
        headers=auth(),
        json={"payment_option_id": "paypal", "idempotency_key": "x"},
    )

    assert response.status_code == 404


def test_cancelling_a_payment_cancels_the_order(client: TestClient, product: Product) -> None:
    order = create_order(client, product)
    client.post(
        f"/api/v1/orders/{order['id']}/payments/tbank",
        headers=auth(),
        json={"payment_option_id": "tbank-card", "idempotency_key": "checkout-1"},
    )

    cancelled = client.post(f"/api/v1/orders/{order['id']}/payment/cancel", headers=auth())

    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"
    body = client.get(f"/api/v1/orders/{order['id']}", headers=auth()).json()
    assert body["status"] == "cancelled"


def test_orders_are_listed_for_the_owner(client: TestClient, product: Product) -> None:
    create_order(client, product)
    create_order(client, product)

    response = client.get("/api/v1/orders", headers=auth())

    assert response.status_code == 200
    assert len(response.json()) == 2
    assert all(UUID(order["id"]) for order in response.json())


def test_quantity_must_be_positive(client: TestClient, product: Product) -> None:
    response = client.post(
        "/api/v1/orders",
        headers=auth(),
        json={
            "items": [{"product_id": str(product.id), "quantity": 0}],
            "customer": {"name": "И", "email": "i@e.com", "phone": "+70000000000"},
        },
    )

    assert response.status_code == 422


def test_missing_order_is_a_404(client: TestClient) -> None:
    response = client.get(f"/api/v1/orders/{USER_ID}", headers=auth())

    assert response.status_code == 404
