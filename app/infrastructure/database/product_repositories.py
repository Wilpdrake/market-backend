import builtins
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.products.models import Product
from app.domain.tags.models import Tag
from app.infrastructure.database.models import ProductModel, ProductTagModel, TagModel


def _tag_entity(model: TagModel) -> Tag:
    return Tag(
        id=model.id,
        name=model.name,
        slug=model.slug,
        description=model.description,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _to_entity(model: ProductModel, tags: list[Tag]) -> Product:
    return Product(
        id=model.id,
        title=model.title,
        description=model.description,
        images=model.images,
        header_image=model.header_image,
        price=model.price,
        ozon_price=model.ozon_price,
        wb_price=model.wb_price,
        tags=tags,
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
        self.session.add_all(
            ProductTagModel(product_id=product.id, tag_id=tag.id) for tag in product.tags
        )
        await self.session.commit()
        await self.session.refresh(model)
        return _to_entity(model, await self._tags(product.id))

    async def get_by_id(self, product_id: UUID) -> Product | None:
        model = await self.session.get(ProductModel, product_id)
        return _to_entity(model, await self._tags(product_id)) if model else None

    async def list(self, *, offset: int, limit: int) -> list[Product]:
        models = list(
            await self.session.scalars(
                select(ProductModel)
                .order_by(ProductModel.created_at.desc())
                .offset(offset)
                .limit(limit)
            )
        )
        return [_to_entity(model, await self._tags(model.id)) for model in models]

    async def save(self, product: Product) -> Product:
        model = await self.session.get(ProductModel, product.id)
        if model is None:
            raise LookupError("Product not found")
        for name, value in self._values(product).items():
            setattr(model, name, value)
        await self.session.execute(
            delete(ProductTagModel).where(ProductTagModel.product_id == product.id)
        )
        self.session.add_all(
            ProductTagModel(product_id=product.id, tag_id=tag.id) for tag in product.tags
        )
        await self.session.commit()
        await self.session.refresh(model)
        return _to_entity(model, await self._tags(product.id))

    async def delete(self, product_id: UUID) -> None:
        await self.session.execute(delete(ProductModel).where(ProductModel.id == product_id))
        await self.session.commit()

    async def _tags(self, product_id: UUID) -> builtins.list[Tag]:
        models = await self.session.scalars(
            select(TagModel)
            .join(ProductTagModel, ProductTagModel.tag_id == TagModel.id)
            .where(ProductTagModel.product_id == product_id)
            .order_by(TagModel.name.asc())
        )
        return [_tag_entity(model) for model in models]

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
