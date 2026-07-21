from uuid import UUID

from dishka.integrations.fastapi import FromDishka, inject
from fastapi import APIRouter, Query, Response, status

from app.application.products.dto import CreateProduct, UpdateProduct
from app.application.products.services import ProductService
from app.application.users.services import AuthService
from app.domain.products.entities import Product
from app.presentation.api.v1.admin.dependencies import current_admin
from app.presentation.api.v1.admin.schemas import (
    ProductCreateRequest,
    ProductResponse,
    ProductUpdateRequest,
)
from app.presentation.api.v1.auth import AuthorizationHeader

router = APIRouter(prefix="/products")


@router.get("", response_model=list[ProductResponse])
@inject
async def list_products(
    authorization: AuthorizationHeader,
    auth: FromDishka[AuthService],
    service: FromDishka[ProductService],
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=100),
) -> list[Product]:
    await current_admin(authorization, auth)
    return await service.list(offset=offset, limit=limit)


@router.post("", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
@inject
async def create_product(
    data: ProductCreateRequest,
    authorization: AuthorizationHeader,
    auth: FromDishka[AuthService],
    service: FromDishka[ProductService],
) -> Product:
    actor = await current_admin(authorization, auth)
    return await service.create(CreateProduct(**data.model_dump()), actor_id=actor.id)


@router.get("/{product_id}", response_model=ProductResponse)
@inject
async def get_product(
    product_id: UUID,
    authorization: AuthorizationHeader,
    auth: FromDishka[AuthService],
    service: FromDishka[ProductService],
) -> Product:
    await current_admin(authorization, auth)
    return await service.get(product_id)


@router.patch("/{product_id}", response_model=ProductResponse)
@inject
async def update_product(
    product_id: UUID,
    data: ProductUpdateRequest,
    authorization: AuthorizationHeader,
    auth: FromDishka[AuthService],
    service: FromDishka[ProductService],
) -> Product:
    actor = await current_admin(authorization, auth)
    return await service.update(
        product_id,
        UpdateProduct(
            **data.model_dump(),
            clear_fields=frozenset(
                name for name in data.model_fields_set if getattr(data, name) is None
            ),
        ),
        actor_id=actor.id,
    )


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
@inject
async def delete_product(
    product_id: UUID,
    authorization: AuthorizationHeader,
    auth: FromDishka[AuthService],
    service: FromDishka[ProductService],
) -> Response:
    await current_admin(authorization, auth)
    await service.delete(product_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
