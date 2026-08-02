from uuid import UUID

from dishka.integrations.fastapi import FromDishka, inject
from fastapi import APIRouter, Query, Response, status

from app.application.users.exceptions import PermissionDeniedError
from app.application.users.models import CreateUser, UpdateUser
from app.application.users.services import AuthService, UserService
from app.domain.users.models import User
from app.presentation.api.v1.admin.dependencies import current_admin
from app.presentation.api.v1.admin.schemas import (
    AdminUserCreateRequest,
    AdminUserResponse,
    AdminUserUpdateRequest,
)
from app.presentation.api.v1.auth import AuthorizationHeader

router = APIRouter(prefix="/users")


@router.get("", response_model=list[AdminUserResponse])
@inject
async def list_users(
    authorization: AuthorizationHeader,
    auth: FromDishka[AuthService],
    service: FromDishka[UserService],
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=100),
) -> list[User]:
    await current_admin(authorization, auth)
    return await service.list(offset=offset, limit=limit)


@router.post("", response_model=AdminUserResponse, status_code=status.HTTP_201_CREATED)
@inject
async def create_user(
    data: AdminUserCreateRequest,
    authorization: AuthorizationHeader,
    auth: FromDishka[AuthService],
    service: FromDishka[UserService],
) -> User:
    actor = await current_admin(authorization, auth)
    return await service.create(
        CreateUser(
            email=str(data.email),
            username=data.username,
            password=data.password,
            phone=data.contact_number,
            name=data.name,
            surname=data.surname,
            patronymic=data.patronymic,
            telegram_username=data.telegram_username,
            comment=data.comment,
            avatar_image=data.avatar_image,
            header_image=data.header_image,
            role=data.role,
            created_by=actor.id,
        ),
        actor=actor,
    )


@router.get("/{user_id}", response_model=AdminUserResponse)
@inject
async def get_user(
    user_id: UUID,
    authorization: AuthorizationHeader,
    auth: FromDishka[AuthService],
    service: FromDishka[UserService],
) -> User:
    await current_admin(authorization, auth)
    return await service.get(user_id)


@router.patch("/{user_id}", response_model=AdminUserResponse)
@inject
async def update_user(
    user_id: UUID,
    data: AdminUserUpdateRequest,
    authorization: AuthorizationHeader,
    auth: FromDishka[AuthService],
    service: FromDishka[UserService],
) -> User:
    actor = await current_admin(authorization, auth)
    return await service.update(
        user_id,
        UpdateUser(
            email=str(data.email) if data.email else None,
            username=data.username,
            phone=data.contact_number,
            is_active=data.is_active,
            name=data.name,
            surname=data.surname,
            patronymic=data.patronymic,
            telegram_username=data.telegram_username,
            comment=data.comment,
            avatar_image=data.avatar_image,
            header_image=data.header_image,
            role=data.role,
            password=data.password,
            clear_fields=frozenset(
                {
                    "phone" if name == "contact_number" else name
                    for name in data.model_fields_set
                    if getattr(data, name) is None
                }
            ),
        ),
        actor=actor,
    )


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
@inject
async def delete_user(
    user_id: UUID,
    authorization: AuthorizationHeader,
    auth: FromDishka[AuthService],
    service: FromDishka[UserService],
) -> Response:
    actor = await current_admin(authorization, auth)
    if actor.id == user_id:
        raise PermissionDeniedError("An administrator cannot delete their own account")
    await service.delete(user_id, actor=actor)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
