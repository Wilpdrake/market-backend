from uuid import UUID

from dishka.integrations.fastapi import FromDishka, inject
from fastapi import APIRouter, Response, status

from app.application.users.dto import UpdateUser
from app.application.users.exceptions import PermissionDeniedError
from app.application.users.services import AuthService, UserService
from app.domain.users.entities import User
from app.presentation.api.v1.auth import AuthorizationHeader, current_user
from app.presentation.api.v1.schemas import UpdateUserRequest, UserResponse

router = APIRouter(prefix="/users", tags=["users"])


async def _actor(authorization: str | None, auth: AuthService) -> User:
    return await current_user(authorization, auth)


@router.get("/me", response_model=UserResponse)
@inject
async def me(authorization: AuthorizationHeader, auth: FromDishka[AuthService]) -> User:
    return await _actor(authorization, auth)


@router.get("", response_model=list[UserResponse])
@inject
async def list_users(
    authorization: AuthorizationHeader,
    auth: FromDishka[AuthService],
    service: FromDishka[UserService],
    offset: int = 0,
    limit: int = 100,
) -> list[User]:
    actor = await _actor(authorization, auth)
    if not actor.is_superuser:
        raise PermissionDeniedError("Administrator privileges required")
    return await service.list(offset=offset, limit=min(limit, 100))


@router.get("/{user_id}", response_model=UserResponse)
@inject
async def get_user(
    user_id: UUID,
    authorization: AuthorizationHeader,
    auth: FromDishka[AuthService],
    service: FromDishka[UserService],
) -> User:
    actor = await _actor(authorization, auth)
    if actor.id != user_id and not actor.is_superuser:
        raise PermissionDeniedError("Access denied")
    return await service.get(user_id)


@router.patch("/{user_id}", response_model=UserResponse)
@inject
async def update_user(
    user_id: UUID,
    data: UpdateUserRequest,
    authorization: AuthorizationHeader,
    auth: FromDishka[AuthService],
    service: FromDishka[UserService],
) -> User:
    actor = await _actor(authorization, auth)
    if actor.id != user_id and not actor.is_superuser:
        raise PermissionDeniedError("Access denied")
    return await service.update(
        user_id,
        UpdateUser(
            email=str(data.email) if data.email else None,
            phone=data.phone,
            is_active=data.is_active,
        ),
    )


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
@inject
async def delete_user(
    user_id: UUID,
    authorization: AuthorizationHeader,
    auth: FromDishka[AuthService],
    service: FromDishka[UserService],
) -> Response:
    actor = await _actor(authorization, auth)
    if actor.id != user_id and not actor.is_superuser:
        raise PermissionDeniedError("Access denied")
    await service.delete(user_id, actor=actor)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
