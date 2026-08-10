from typing import cast
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.orders.models import CrmStatus, Customer, Order, OrderItem, OrderStatus
from app.infrastructure.database.models import OrderItemModel, OrderModel


def _to_entity(model: OrderModel, items: list[OrderItemModel]) -> Order:
    return Order(
        id=model.id,
        user_id=model.user_id,
        status=cast(OrderStatus, model.status),
        crm_status=cast(CrmStatus, model.crm_status),
        currency=model.currency,
        customer=Customer(
            name=model.customer_name,
            email=model.customer_email,
            phone=model.customer_phone,
        ),
        items=[
            OrderItem(
                id=item.id,
                product_id=item.product_id,
                title=item.title,
                quantity=item.quantity,
                unit_price=item.unit_price,
            )
            for item in items
        ],
        comment=model.comment,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


class SqlAlchemyOrderRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, order: Order) -> Order:
        model = OrderModel(
            id=order.id,
            user_id=order.user_id,
            status=order.status,
            crm_status=order.crm_status,
            currency=order.currency,
            customer_name=order.customer.name,
            customer_email=order.customer.email,
            customer_phone=order.customer.phone,
            comment=order.comment,
            created_at=order.created_at,
            updated_at=order.updated_at,
        )
        self.session.add(model)
        # Flush the parent explicitly because the ORM models have no relationship configured;
        # otherwise SQLAlchemy may insert order_items before orders in the same unit of work.
        await self.session.flush()
        self.session.add_all(
            OrderItemModel(
                id=item.id,
                order_id=order.id,
                product_id=item.product_id,
                title=item.title,
                quantity=item.quantity,
                unit_price=item.unit_price,
            )
            for item in order.items
        )
        await self.session.commit()
        await self.session.refresh(model)
        return _to_entity(model, await self._items(order.id))

    async def get_by_id(self, order_id: UUID) -> Order | None:
        model = await self.session.get(OrderModel, order_id)
        if model is None:
            return None
        return _to_entity(model, await self._items(order_id))

    async def list_for_user(self, user_id: UUID, *, offset: int, limit: int) -> list[Order]:
        models = list(
            await self.session.scalars(
                select(OrderModel)
                .where(OrderModel.user_id == user_id)
                .order_by(OrderModel.created_at.desc())
                .offset(offset)
                .limit(limit)
            )
        )
        return [_to_entity(model, await self._items(model.id)) for model in models]

    async def list_all(self, *, offset: int, limit: int) -> list[Order]:
        models = list(
            await self.session.scalars(
                select(OrderModel)
                .order_by(OrderModel.created_at.desc())
                .offset(offset)
                .limit(limit)
            )
        )
        return [_to_entity(model, await self._items(model.id)) for model in models]

    async def save(self, order: Order) -> Order:
        model = await self.session.get(OrderModel, order.id)
        if model is None:
            raise LookupError("Order not found")
        model.status = order.status
        model.crm_status = order.crm_status
        model.currency = order.currency
        model.customer_name = order.customer.name
        model.customer_email = order.customer.email
        model.customer_phone = order.customer.phone
        model.comment = order.comment
        model.updated_at = order.updated_at
        await self.session.commit()
        await self.session.refresh(model)
        return _to_entity(model, await self._items(order.id))

    async def _items(self, order_id: UUID) -> list[OrderItemModel]:
        return list(
            await self.session.scalars(
                select(OrderItemModel).where(OrderItemModel.order_id == order_id)
            )
        )
