from decimal import Decimal
from uuid import UUID

from app.application.products.dto import CreateProduct, UpdateProduct
from app.application.products.services import ProductService
from app.domain.products.entities import Product


class InMemoryProductRepository:
    def __init__(self) -> None:
        self.products: dict[UUID, Product] = {}

    async def add(self, product: Product) -> Product:
        self.products[product.id] = product
        return product

    async def get_by_id(self, product_id: UUID) -> Product | None:
        return self.products.get(product_id)

    async def list(self, *, offset: int, limit: int) -> list[Product]:
        return list(self.products.values())[offset : offset + limit]

    async def save(self, product: Product) -> Product:
        self.products[product.id] = product
        return product

    async def delete(self, product_id: UUID) -> None:
        self.products.pop(product_id, None)


async def test_product_crud_tracks_admin_authors() -> None:
    repository = InMemoryProductRepository()
    service = ProductService(repository)
    admin_id = UUID("00000000-0000-0000-0000-000000000001")

    created = await service.create(
        CreateProduct(
            title="Хохломская тарелка",
            description="Ручная работа",
            images=["https://example.com/plate-1.jpg"],
            header_image="https://example.com/plate-cover.jpg",
            price=Decimal("2500.00"),
            ozon_price=Decimal("2700.00"),
            wb_price=None,
        ),
        actor_id=admin_id,
    )
    updated = await service.update(
        created.id,
        UpdateProduct(
            price=Decimal("14.00"),
            images=["one.jpg"],
            clear_fields=frozenset({"description"}),
        ),
        actor_id=admin_id,
    )
    await service.delete(updated.id)

    assert updated.price == Decimal("14.00")
    assert updated.images == ["one.jpg"]
    assert updated.description is None
    assert updated.created_by == admin_id
    assert updated.updated_by == admin_id
    assert updated.id not in repository.products
