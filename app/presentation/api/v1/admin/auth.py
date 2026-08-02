from dishka.integrations.fastapi import FromDishka, inject
from fastapi import APIRouter

from app.application.users.models import AccessToken
from app.application.users.services import AuthService
from app.domain.users.models import User
from app.presentation.api.v1.admin.dependencies import current_admin
from app.presentation.api.v1.admin.schemas import AdminLoginRequest, AdminUserResponse
from app.presentation.api.v1.auth import AuthorizationHeader
from app.presentation.api.v1.schemas import TokenResponse

router = APIRouter(prefix="/auth")


@router.post("/token", response_model=TokenResponse)
@inject
async def login(data: AdminLoginRequest, service: FromDishka[AuthService]) -> AccessToken:
    return await service.admin_login(str(data.email), data.password)


@router.get("/me", response_model=AdminUserResponse)
@inject
async def me(
    authorization: AuthorizationHeader,
    service: FromDishka[AuthService],
) -> User:
    return await current_admin(authorization, service)
