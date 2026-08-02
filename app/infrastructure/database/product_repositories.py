from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.products.models import Product
from app.infrastructure.database.models import ProductModel


def _to_entity(model: ProductModel) -> Product:
    return Product(
        id=model.id,
        title=model.title,
        description=model.description,
        images=model.images,
        header_image=model.header_image,
        price=model.price,
        ozon_price=model.ozon_price,
        wb_price=model.wb_price,
        created_by=model.created_by,
        updated_by=model.updated_by,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


class SqlAlchemyProductRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, product: Product) -> Product:
        model = ProductModel(**self._values(product))
        self.session.add(model)
        await self.session.commit()
        await self.session.refresh(model)
        return _to_entity(model)

    async def get_by_id(self, product_id: UUID) -> Product | None:
        model = await self.session.get(ProductModel, product_id)
        return _to_entity(model) if model else None

    async def list(self, *, offset: int, limit: int) -> list[Product]:
        models = await self.session.scalars(
            select(ProductModel)
            .order_by(ProductModel.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return [_to_entity(model) for model in models]

    async def save(self, product: Product) -> Product:
        model = await self.session.get(ProductModel, product.id)
        if model is None:
            raise LookupError("Product not found")
        for name, value in self._values(product).items():
            setattr(model, name, value)
        await self.session.commit()
        await self.session.refresh(model)
        return _to_entity(model)

    async def delete(self, product_id: UUID) -> None:
        await self.session.execute(delete(ProductModel).where(ProductModel.id == product_id))
        await self.session.commit()

    @staticmethod
    def _values(product: Product) -> dict[str, object]:
        return {
            "id": product.id,
            "title": product.title,
            "description": product.description,
            "images": product.images,
            "header_image": product.header_image,
            "price": product.price,
            "ozon_price": product.ozon_price,
            "wb_price": product.wb_price,
            "created_by": product.created_by,
            "updated_by": product.updated_by,
            "created_at": product.created_at,
            "updated_at": product.updated_at,
        }
