from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class CreateProduct:
    title: str
    description: str | None = None
    images: list[str] | None = None
    header_image: str | None = None
    price: Decimal | None = None
    ozon_price: Decimal | None = None
    wb_price: Decimal | None = None


@dataclass(frozen=True, slots=True)
class UpdateProduct:
    title: str | None = None
    description: str | None = None
    images: list[str] | None = None
    header_image: str | None = None
    price: Decimal | None = None
    ozon_price: Decimal | None = None
    wb_price: Decimal | None = None
    clear_fields: frozenset[str] = frozenset()
