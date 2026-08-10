"""Read-only product catalog used by the public storefront.

Administrative mutations live under ``/admin/products``.  Keeping public reads in a
separate router makes the authorization boundary visible and prevents the shop UI from
needing an administrator token.
"""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from dishka.integrations.fastapi import FromDishka, inject
from fastapi import APIRouter, Query
from pydantic import ConfigDict, Field

from app.application.products.services import ProductService
from app.domain.products.models import Product
from app.models import ApiResponseModel
from app.presentation.api.v1.admin.schemas import TagSummary

router = APIRouter(prefix="/products", tags=["products"])


class PublicProductResponse(ApiResponseModel):
    """Storefront representation deliberately excludes administrator identifiers."""

    model_config = ConfigDict(populate_by_name=True)

    uuid: UUID = Field(validation_alias="id")
    title: str
    description: str | None
    images: list[str] | None
    header_image: str | None
    price: Decimal | None
    ozon_price: Decimal | None
    wb_price: Decimal | None
    tags: list[TagSummary]
    created_at: datetime
    updated_at: datetime


@router.get("", response_model=list[PublicProductResponse])
@inject
async def list_products(
    service: FromDishka[ProductService],
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=100),
) -> list[Product]:
    """Return a bounded page of products without requiring authentication."""
    return await service.list(offset=offset, limit=limit)


@router.get("/{product_id}", response_model=PublicProductResponse)
@inject
async def get_product(product_id: UUID, service: FromDishka[ProductService]) -> Product:
    """Return one public product card or the common domain-level 404 response."""
    return await service.get(product_id)
