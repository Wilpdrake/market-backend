"""T-Bank checkout endpoints.

``POST /orders/{order_id}/payments/tbank`` is idempotent per ``idempotency_key``: a replayed
request answers 200 with the stored payment, while a fresh attempt answers 201.

The provider webhook is unauthenticated by design — it is verified with the T-Bank ``Token``
signature instead — and must answer with the literal body ``OK``.
"""

from json import JSONDecodeError
from typing import Any
from uuid import UUID

from dishka.integrations.fastapi import FromDishka, inject
from fastapi import APIRouter, HTTPException, Request, Response, status

from app.application.payments.services import PaymentService
from app.application.users.services import AuthService
from app.presentation.api.v1.auth import AuthorizationHeader, current_user
from app.presentation.api.v1.checkout_schemas import (
    CreateTBankPaymentRequest,
    PaymentResponse,
    TBankPaymentOptionResponse,
)

router = APIRouter(tags=["payments"])


@router.get("/payments/tbank/options", response_model=list[TBankPaymentOptionResponse])
@inject
async def list_tbank_payment_options(
    service: FromDishka[PaymentService],
) -> list[TBankPaymentOptionResponse]:
    """Public payment methods. Only stable slugs are exposed, never a TerminalKey."""
    return [TBankPaymentOptionResponse.model_validate(option) for option in service.options()]


@router.post(
    "/orders/{order_id}/payments/tbank",
    response_model=PaymentResponse,
    status_code=status.HTTP_201_CREATED,
)
@inject
async def create_tbank_payment(
    order_id: UUID,
    data: CreateTBankPaymentRequest,
    response: Response,
    authorization: AuthorizationHeader,
    auth: FromDishka[AuthService],
    service: FromDishka[PaymentService],
) -> PaymentResponse:
    actor = await current_user(authorization, auth)
    payment, created = await service.create(
        order_id,
        data.payment_option_id,
        data.idempotency_key,
        actor=actor,
    )
    if not created:
        response.status_code = status.HTTP_200_OK
    return PaymentResponse.from_domain(payment)


@router.get("/orders/{order_id}/payment", response_model=PaymentResponse)
@inject
async def get_order_payment(
    order_id: UUID,
    authorization: AuthorizationHeader,
    auth: FromDishka[AuthService],
    service: FromDishka[PaymentService],
) -> PaymentResponse:
    actor = await current_user(authorization, auth)
    return PaymentResponse.from_domain(await service.get_for_order(order_id, actor=actor))


@router.post("/orders/{order_id}/payment/cancel", response_model=PaymentResponse)
@inject
async def cancel_order_payment(
    order_id: UUID,
    authorization: AuthorizationHeader,
    auth: FromDishka[AuthService],
    service: FromDishka[PaymentService],
) -> PaymentResponse:
    actor = await current_user(authorization, auth)
    return PaymentResponse.from_domain(await service.cancel(order_id, actor=actor))


@router.post("/payments/tbank/webhook", response_class=Response)
@inject
async def receive_tbank_webhook(
    request: Request,
    service: FromDishka[PaymentService],
) -> Response:
    try:
        payload: Any = await request.json()
    except JSONDecodeError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Malformed notification payload",
        ) from error
    if not isinstance(payload, dict):
        return Response(
            content='{"detail":"Malformed notification payload"}',
            media_type="application/json",
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    if not await service.handle_notification(payload):
        return Response(
            content='{"detail":"Invalid provider signature"}',
            media_type="application/json",
            status_code=status.HTTP_401_UNAUTHORIZED,
        )
    # T-Bank retries for a month unless the body is exactly ``OK``.
    return Response(content="OK", media_type="text/plain")
