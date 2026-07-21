from typing import Annotated

from dishka.integrations.fastapi import FromDishka, inject
from fastapi import APIRouter, Header

from app.application.users.dto import AccessToken, CreateUser
from app.application.users.services import AuthService, UserService
from app.domain.users.entities import User
from app.presentation.api.v1.schemas import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def bearer_token(authorization: str | None) -> str:
    scheme, _, token = (authorization or "").partition(" ")
    if scheme.lower() != "bearer" or not token:
        return ""
    return token


async def current_user(
    authorization: str | None,
    auth_service: AuthService,
) -> User:
    return await auth_service.get_current_user(bearer_token(authorization))


@router.post("/register", response_model=UserResponse, status_code=201)
@inject
async def register(data: RegisterRequest, service: FromDishka[UserService]) -> User:
    return await service.create(
        CreateUser(email=str(data.email), password=data.password, phone=data.phone)
    )


@router.post("/token", response_model=TokenResponse)
@inject
async def login(data: LoginRequest, service: FromDishka[AuthService]) -> AccessToken:
    return await service.login(str(data.email), data.password)


AuthorizationHeader = Annotated[str | None, Header(alias="Authorization")]
