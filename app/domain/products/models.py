from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from pydantic import Field

from app.domain.tags.models import Tag
from app.models import EntityModel


class Product(EntityModel):
    title: str
    created_by: UUID
    updated_by: UUID
    id: UUID = Field(default_factory=uuid4)
    description: str | None = None
    images: list[str] | None = None
    header_image: str | None = None
    price: Decimal | None = None
    ozon_price: Decimal | None = None
    wb_price: Decimal | None = None
    tags: list[Tag] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
