from typing import cast
from uuid import UUID

from dishka.integrations.fastapi import FromDishka, inject
from fastapi import APIRouter, Query, Request, Response, status
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from starlette.datastructures import UploadFile

from app.application.products.models import CreateProduct, UpdateProduct
from app.application.products.services import ProductService
from app.application.users.services import AuthService
from app.core.config import get_settings
from app.domain.products.models import Product
from app.infrastructure.product_images import delete_product_images, store_product_images
from app.presentation.api.v1.admin.dependencies import current_admin
from app.presentation.api.v1.admin.schemas import (
    ProductCreateRequest,
    ProductResponse,
    ProductUpdateRequest,
)
from app.presentation.api.v1.auth import AuthorizationHeader as AuthHeader

router = APIRouter(prefix="/products")

type ProductRequest = ProductCreateRequest | ProductUpdateRequest


async def _parse_product_request[RequestT: ProductRequest](
    request: Request,
    model_type: type[RequestT],
) -> tuple[RequestT, list[UploadFile], int]:
    try:
        if request.headers.get("content-type", "").startswith("multipart/form-data"):
            form = await request.form()
            product = form.get("product")
            if not isinstance(product, str):
                raise RequestValidationError(
                    [{"type": "missing", "loc": ("body", "product"), "msg": "Field required"}]
                )
            data = cast(RequestT, model_type.model_validate_json(product))
            images = [image for image in form.getlist("images") if isinstance(image, UploadFile)]
            raw_cover_index = form.get("cover_index", "0")
            if not isinstance(raw_cover_index, str):
                raise ValueError("cover_index must be an integer")
            return data, images, int(raw_cover_index)

        data = cast(RequestT, model_type.model_validate_json(await request.body()))
        return data, [], 0
    except ValidationError as error:
        raise RequestValidationError(error.errors()) from error
    except ValueError as error:
        raise RequestValidationError(
            [
                {
                    "type": "int_parsing",
                    "loc": ("body", "cover_index"),
                    "msg": "Input should be a valid integer",
                }
            ]
        ) from error


@router.get("", response_model=list[ProductResponse])
@inject
async def list_products(
    auth_header: AuthHeader,
    auth: FromDishka[AuthService],
    service: FromDishka[ProductService],
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=100),
) -> list[Product]:
    await current_admin(auth_header, auth)
    return await service.list(offset=offset, limit=limit)


@router.post("", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
@inject
async def create_product(
    request: Request,
    auth_header: AuthHeader,
    auth: FromDishka[AuthService],
    service: FromDishka[ProductService],
) -> Product:
    data, images, cover_index = await _parse_product_request(request, ProductCreateRequest)
    actor = await current_admin(auth_header, auth)
    stored = None
    if images:
        stored = await store_product_images(
            images,
            cover_index=cover_index,
            upload_dir=get_settings().upload_dir,
        )
        data = ProductCreateRequest.model_validate(
            {**data.model_dump(), "images": stored.urls, "header_image": stored.cover_url}
        )
    try:
        return await service.create(CreateProduct(**data.model_dump()), actor_id=actor.id)
    except Exception:
        if stored is not None:
            await delete_product_images(stored.urls, upload_dir=get_settings().upload_dir)
        raise


@router.get("/{product_id}", response_model=ProductResponse)
@inject
async def get_product(
    product_id: UUID,
    auth_header: AuthHeader,
    auth: FromDishka[AuthService],
    service: FromDishka[ProductService],
) -> Product:
    await current_admin(auth_header, auth)
    return await service.get(product_id)


@router.patch("/{product_id}", response_model=ProductResponse)
@inject
async def update_product(
    product_id: UUID,
    request: Request,
    auth_header: AuthHeader,
    auth: FromDishka[AuthService],
    service: FromDishka[ProductService],
) -> Product:
    data, images, cover_index = await _parse_product_request(request, ProductUpdateRequest)
    actor = await current_admin(auth_header, auth)
    stored = None
    if images:
        stored = await store_product_images(
            images,
            cover_index=cover_index,
            upload_dir=get_settings().upload_dir,
        )
        data = ProductUpdateRequest.model_validate(
            {**data.model_dump(), "images": stored.urls, "header_image": stored.cover_url}
        )
    try:
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
    except Exception:
        if stored is not None:
            await delete_product_images(stored.urls, upload_dir=get_settings().upload_dir)
        raise


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
@inject
async def delete_product(
    product_id: UUID,
    auth_header: AuthHeader,
    auth: FromDishka[AuthService],
    service: FromDishka[ProductService],
) -> Response:
    await current_admin(auth_header, auth)
    await service.delete(product_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
