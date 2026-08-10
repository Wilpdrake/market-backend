from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import ConfigDict, EmailStr, Field

from app.domain.orders.models import Order, OrderItem
from app.domain.payments.models import Payment
from app.models import ApiModel, ApiResponseModel


def money(value: Decimal) -> str:
    """Render money as a fixed two-decimal string; JSON floats must never carry an amount."""
    return f"{value:.2f}"


class CustomerRequest(ApiModel):
    name: str = Field(min_length=1, max_length=200)
    email: EmailStr = Field(max_length=320)
    phone: str = Field(min_length=1, max_length=32)


class CreateOrderItemRequest(ApiModel):
    product_id: UUID
    quantity: int = Field(ge=1, le=1000)


class CreateOrderRequest(ApiModel):
    items: list[CreateOrderItemRequest] = Field(min_length=1, max_length=100)
    customer: CustomerRequest
    comment: str | None = Field(default=None, max_length=2000)


class CustomerResponse(ApiResponseModel):
    name: str
    email: EmailStr
    phone: str


class OrderItemResponse(ApiResponseModel):
    product_id: UUID
    title: str
    quantity: int
    unit_price: str
    total: str

    @classmethod
    def from_domain(cls, item: OrderItem) -> "OrderItemResponse":
        return cls(
            product_id=item.product_id,
            title=item.title,
            quantity=item.quantity,
            unit_price=money(item.unit_price),
            total=money(item.total),
        )


class OrderResponse(ApiResponseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: UUID
    status: str
    items: list[OrderItemResponse]
    total: str
    currency: str
    customer: CustomerResponse
    comment: str | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_domain(cls, order: Order) -> "OrderResponse":
        return cls(
            id=order.id,
            status=order.status,
            items=[OrderItemResponse.from_domain(item) for item in order.items],
            total=money(order.total),
            currency=order.currency,
            customer=CustomerResponse.model_validate(order.customer),
            comment=order.comment,
            created_at=order.created_at,
            updated_at=order.updated_at,
        )


class TBankPaymentOptionResponse(ApiResponseModel):
    id: str
    title: str
    kind: Literal["card", "sbp"]
    enabled: bool


class CreateTBankPaymentRequest(ApiModel):
    payment_option_id: str = Field(min_length=1, max_length=64)
    idempotency_key: str = Field(min_length=1, max_length=64)


class PaymentConfirmationResponse(ApiResponseModel):
    type: Literal["redirect", "qr"]
    url: str


class PaymentResponse(ApiResponseModel):
    id: UUID
    order_id: UUID
    provider: str
    payment_option_id: str
    status: str
    amount: str
    currency: str
    confirmation: PaymentConfirmationResponse | None
    failure_message: str | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_domain(cls, payment: Payment) -> "PaymentResponse":
        return cls(
            id=payment.id,
            order_id=payment.order_id,
            provider=payment.provider,
            payment_option_id=payment.payment_option_id,
            status=payment.status,
            amount=money(payment.amount),
            currency=payment.currency,
            confirmation=(
                PaymentConfirmationResponse.model_validate(payment.confirmation)
                if payment.confirmation
                else None
            ),
            failure_message=payment.failure_message,
            created_at=payment.created_at,
            updated_at=payment.updated_at,
        )


__all__ = [
    "CreateOrderItemRequest",
    "CreateOrderRequest",
    "CreateTBankPaymentRequest",
    "CustomerRequest",
    "CustomerResponse",
    "OrderItemResponse",
    "OrderResponse",
    "PaymentConfirmationResponse",
    "PaymentResponse",
    "TBankPaymentOptionResponse",
    "money",
]
