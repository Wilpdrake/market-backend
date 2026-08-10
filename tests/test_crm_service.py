from decimal import Decimal
from uuid import UUID

from app.application.orders.services import OrderService
from app.domain.orders.models import Customer, Order, OrderItem

ORDER_ID = UUID("00000000-0000-0000-0000-000000000010")
USER_ID = UUID("00000000-0000-0000-0000-000000000011")
PRODUCT_ID = UUID("00000000-0000-0000-0000-000000000012")


class InMemoryOrderRepository:
    def __init__(self, order: Order) -> None:
        self.order = order

    async def add(self, order: Order) -> Order:
        self.order = order
        return order

    async def get_by_id(self, order_id: UUID) -> Order | None:
        return self.order if self.order.id == order_id else None

    async def list_for_user(self, user_id: UUID, *, offset: int, limit: int) -> list[Order]:
        return [self.order] if self.order.user_id == user_id else []

    async def list_all(self, *, offset: int, limit: int) -> list[Order]:
        return [self.order][offset : offset + limit]

    async def save(self, order: Order) -> Order:
        self.order = order
        return order


class UnusedProductRepository:
    pass


def order() -> Order:
    return Order(
        id=ORDER_ID,
        user_id=USER_ID,
        customer=Customer(name="Customer", email="customer@example.com", phone="+70000000000"),
        items=[
            OrderItem(
                product_id=PRODUCT_ID,
                title="Plate",
                quantity=2,
                unit_price=Decimal("1250.00"),
            )
        ],
    )


async def test_crm_lists_all_orders_and_updates_independent_fulfilment_status() -> None:
    repository = InMemoryOrderRepository(order())
    service = OrderService(repository, UnusedProductRepository())  # type: ignore[arg-type]

    listed = await service.list_all(offset=0, limit=100)
    updated = await service.set_crm_status(listed[0], "assembling")

    assert listed[0].total == Decimal("2500.00")
    assert updated.crm_status == "assembling"
    assert updated.status == "new"
