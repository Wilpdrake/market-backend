from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4


@dataclass(slots=True)
class Product:
    title: str
    created_by: UUID
    updated_by: UUID
    id: UUID = field(default_factory=uuid4)
    description: str | None = None
    images: list[str] | None = None
    header_image: str | None = None
    price: Decimal | None = None
    ozon_price: Decimal | None = None
    wb_price: Decimal | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
