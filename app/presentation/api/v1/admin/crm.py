from uuid import UUID

from dishka.integrations.fastapi import FromDishka, inject
from fastapi import APIRouter, Query, Request

from app.application.audit.services import AuditService
from app.application.orders.services import OrderService
from app.application.users.services import AuthService
from app.presentation.api.v1.admin.dependencies import current_admin
from app.presentation.api.v1.admin.schemas import CrmOrderResponse, CrmOrderUpdateRequest
from app.presentation.api.v1.auth import AuthorizationHeader as AuthHeader

router = APIRouter(prefix="/orders")


@router.get("", response_model=list[CrmOrderResponse])
@inject
async def list_orders(
    auth_header: AuthHeader,
    auth: FromDishka[AuthService],
    service: FromDishka[OrderService],
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=100),
) -> list[CrmOrderResponse]:
    await current_admin(auth_header, auth)
    return [
        CrmOrderResponse.from_domain(order)
        for order in await service.list_all(offset=offset, limit=limit)
    ]


@router.patch("/{order_id}", response_model=CrmOrderResponse)
@inject
async def update_order_status(
    order_id: UUID,
    data: CrmOrderUpdateRequest,
    request: Request,
    auth_header: AuthHeader,
    auth: FromDishka[AuthService],
    orders: FromDishka[OrderService],
    audit: FromDishka[AuditService],
) -> CrmOrderResponse:
    actor = await current_admin(auth_header, auth)
    order = await orders.get(order_id)
    previous = order.crm_status
    updated = await orders.set_crm_status(order, data.status)
    if previous != updated.crm_status:
        await audit.record(
            actor=actor,
            action="crm.status_changed",
            entity_type="order",
            entity_id=str(order.id),
            details=f"{previous} → {updated.crm_status}",
            ip_address=request.client.host if request.client else None,
        )
    return CrmOrderResponse.from_domain(updated)
