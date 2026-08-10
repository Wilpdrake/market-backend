from typing import Annotated

from dishka.integrations.fastapi import FromDishka, inject
from fastapi import APIRouter, Depends, Header

from app.application.users.models import AccessToken, CreateUser
from app.application.users.services import AuthService, UserService
from app.domain.users.models import User
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


def _authorization_header(
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
) -> str | None:
    """Read the Authorization header without making it mandatory.

    Declaring the header directly on a handler makes FastAPI answer a missing header with 422,
    which reads as a malformed request. Authentication is not a validation concern: an absent
    header must reach the auth service and surface as 401, which is what the storefront's
    ``onUnauthorized`` hook reacts to.
    """
    return authorization


AuthorizationHeader = Annotated[str | None, Depends(_authorization_header)]
