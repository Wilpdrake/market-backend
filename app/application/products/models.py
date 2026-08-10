from decimal import Decimal
from uuid import UUID

from app.models import CommandModel


class CreateProduct(CommandModel):
    title: str
    description: str | None = None
    images: list[str] | None = None
    header_image: str | None = None
    price: Decimal | None = None
    ozon_price: Decimal | None = None
    wb_price: Decimal | None = None
    tag_ids: tuple[UUID, ...] = ()


class UpdateProduct(CommandModel):
    title: str | None = None
    description: str | None = None
    images: list[str] | None = None
    header_image: str | None = None
    price: Decimal | None = None
    ozon_price: Decimal | None = None
    wb_price: Decimal | None = None
    tag_ids: tuple[UUID, ...] | None = None
    clear_fields: frozenset[str] = frozenset()
