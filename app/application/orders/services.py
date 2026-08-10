"""Order use cases.

Every monetary value is resolved from the catalog inside this service. The HTTP layer accepts
product identifiers and quantities only, so a client cannot influence the amount it is charged.
"""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from app.application.orders.models import CreateOrder
from app.application.orders.ports import OrderRepository
from app.application.products.ports import ProductRepository
from app.application.users.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from app.domain.orders.models import CrmStatus, Customer, Order, OrderItem, OrderStatus
from app.domain.users.models import User
from app.models import replace_model as replace


class OrderService:
    def __init__(self, orders: OrderRepository, products: ProductRepository) -> None:
        self.orders = orders
        self.products = products

    async def create(self, data: CreateOrder, *, actor: User) -> Order:
        items: list[OrderItem] = []
        for requested in data.items:
            product = await self.products.get_by_id(requested.product_id)
            if product is None:
                raise NotFoundError(f"Product {requested.product_id} not found")
            if product.price is None:
                raise ConflictError(f"Product {product.title} is not available for purchase")
            items.append(
                OrderItem(
                    product_id=product.id,
                    title=product.title,
                    quantity=requested.quantity,
                    unit_price=Decimal(product.price),
                )
            )

        return await self.orders.add(
            Order(
                user_id=actor.id,
                customer=Customer(
                    name=data.customer.name,
                    email=data.customer.email,
                    phone=data.customer.phone,
                ),
                items=items,
                comment=data.comment,
            )
        )

    async def get(self, order_id: UUID) -> Order:
        order = await self.orders.get_by_id(order_id)
        if order is None:
            raise NotFoundError("Order not found")
        return order

    async def get_for_actor(self, order_id: UUID, *, actor: User) -> Order:
        """Return an order the actor may read; administrators may read any order."""
        order = await self.get(order_id)
        if order.user_id != actor.id and not actor.is_superuser:
            raise PermissionDeniedError("Access denied")
        return order

    async def list_for_actor(
        self,
        *,
        actor: User,
        offset: int = 0,
        limit: int = 100,
    ) -> list[Order]:
        return await self.orders.list_for_user(actor.id, offset=offset, limit=limit)

    async def list_all(self, *, offset: int = 0, limit: int = 100) -> list[Order]:
        return await self.orders.list_all(offset=offset, limit=limit)

    async def set_crm_status(self, order: Order, status: CrmStatus) -> Order:
        if order.crm_status == status:
            return order
        return await self.orders.save(
            replace(order, crm_status=status, updated_at=datetime.now(UTC))
        )

    async def set_status(self, order: Order, status: OrderStatus) -> Order:
        if order.status == status:
            return order
        return await self.orders.save(replace(order, status=status, updated_at=datetime.now(UTC)))
