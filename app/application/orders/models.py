from uuid import UUID

from pydantic import Field

from app.models import CommandModel


class CreateOrderItem(CommandModel):
    product_id: UUID
    quantity: int = Field(ge=1, le=1000)


class CreateOrderCustomer(CommandModel):
    name: str = Field(min_length=1, max_length=200)
    email: str = Field(min_length=3, max_length=320)
    phone: str = Field(min_length=1, max_length=32)


class CreateOrder(CommandModel):
    items: tuple[CreateOrderItem, ...] = Field(min_length=1, max_length=100)
    customer: CreateOrderCustomer
    comment: str | None = Field(default=None, max_length=2000)
