from dataclasses import replace
from datetime import UTC, datetime
from uuid import UUID

from app.application.products.dto import CreateProduct, UpdateProduct
from app.application.products.ports import ProductRepository
from app.application.users.exceptions import NotFoundError
from app.domain.products.entities import Product


class ProductService:
    def __init__(self, repository: ProductRepository) -> None:
        self.repository = repository

    async def create(self, data: CreateProduct, *, actor_id: UUID) -> Product:
        return await self.repository.add(
            Product(
                title=data.title,
                description=data.description,
                images=data.images,
                header_image=data.header_image,
                price=data.price,
                ozon_price=data.ozon_price,
                wb_price=data.wb_price,
                created_by=actor_id,
                updated_by=actor_id,
            )
        )

    async def get(self, product_id: UUID) -> Product:
        product = await self.repository.get_by_id(product_id)
        if product is None:
            raise NotFoundError("Product not found")
        return product

    async def list(self, *, offset: int = 0, limit: int = 100) -> list[Product]:
        return await self.repository.list(offset=offset, limit=limit)

    async def update(
        self,
        product_id: UUID,
        data: UpdateProduct,
        *,
        actor_id: UUID,
    ) -> Product:
        product = await self.get(product_id)
        return await self.repository.save(
            replace(
                product,
                title=data.title if data.title is not None else product.title,
                description=(
                    None
                    if "description" in data.clear_fields
                    else data.description
                    if data.description is not None
                    else product.description
                ),
                images=(
                    None
                    if "images" in data.clear_fields
                    else data.images
                    if data.images is not None
                    else product.images
                ),
                header_image=(
                    None
                    if "header_image" in data.clear_fields
                    else data.header_image
                    if data.header_image is not None
                    else product.header_image
                ),
                price=(
                    None
                    if "price" in data.clear_fields
                    else data.price
                    if data.price is not None
                    else product.price
                ),
                ozon_price=(
                    None
                    if "ozon_price" in data.clear_fields
                    else data.ozon_price
                    if data.ozon_price is not None
                    else product.ozon_price
                ),
                wb_price=(
                    None
                    if "wb_price" in data.clear_fields
                    else data.wb_price
                    if data.wb_price is not None
                    else product.wb_price
                ),
                updated_by=actor_id,
                updated_at=datetime.now(UTC),
            )
        )

    async def delete(self, product_id: UUID) -> None:
        await self.get(product_id)
        await self.repository.delete(product_id)
