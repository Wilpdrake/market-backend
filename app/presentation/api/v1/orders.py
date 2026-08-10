"""Customer-facing order endpoints.

Orders are always created for the authenticated user; the price of every line item is resolved
server-side from the catalog.
"""

from uuid import UUID

from dishka.integrations.fastapi import FromDishka, inject
from fastapi import APIRouter, Query, status

from app.application.orders.models import CreateOrder, CreateOrderCustomer, CreateOrderItem
from app.application.orders.services import OrderService
from app.application.users.services import AuthService
from app.presentation.api.v1.auth import AuthorizationHeader, current_user
from app.presentation.api.v1.checkout_schemas import CreateOrderRequest, OrderResponse

router = APIRouter(prefix="/orders", tags=["orders"])


@router.post("", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
@inject
async def create_order(
    data: CreateOrderRequest,
    authorization: AuthorizationHeader,
    auth: FromDishka[AuthService],
    service: FromDishka[OrderService],
) -> OrderResponse:
    actor = await current_user(authorization, auth)
    order = await service.create(
        CreateOrder(
            items=tuple(
                CreateOrderItem(product_id=item.product_id, quantity=item.quantity)
                for item in data.items
            ),
            customer=CreateOrderCustomer(
                name=data.customer.name,
                email=str(data.customer.email),
                phone=data.customer.phone,
            ),
            comment=data.comment,
        ),
        actor=actor,
    )
    return OrderResponse.from_domain(order)


@router.get("", response_model=list[OrderResponse])
@inject
async def list_orders(
    authorization: AuthorizationHeader,
    auth: FromDishka[AuthService],
    service: FromDishka[OrderService],
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=100),
) -> list[OrderResponse]:
    actor = await current_user(authorization, auth)
    orders = await service.list_for_actor(actor=actor, offset=offset, limit=limit)
    return [OrderResponse.from_domain(order) for order in orders]


@router.get("/{order_id}", response_model=OrderResponse)
@inject
async def get_order(
    order_id: UUID,
    authorization: AuthorizationHeader,
    auth: FromDishka[AuthService],
    service: FromDishka[OrderService],
) -> OrderResponse:
    actor = await current_user(authorization, auth)
    return OrderResponse.from_domain(await service.get_for_actor(order_id, actor=actor))
