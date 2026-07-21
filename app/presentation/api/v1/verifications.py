from dishka.integrations.fastapi import FromDishka, inject
from fastapi import APIRouter

from app.application.users.services import AuthService, UserService
from app.core.config import Settings
from app.domain.users.entities import User
from app.presentation.api.v1.auth import AuthorizationHeader, current_user
from app.presentation.api.v1.schemas import (
    TelegramLinkResponse,
    UserResponse,
    VerificationTokenRequest,
)

router = APIRouter(prefix="/verifications", tags=["verifications"])


@router.post("/email/request", status_code=202)
@inject
async def request_email(
    authorization: AuthorizationHeader,
    auth: FromDishka[AuthService],
    users: FromDishka[UserService],
) -> dict[str, str]:
    user = await current_user(authorization, auth)
    await users.request_email_verification(user.id)
    return {"status": "accepted"}


@router.post("/email/confirm", response_model=UserResponse)
@inject
async def confirm_email(
    data: VerificationTokenRequest,
    users: FromDishka[UserService],
) -> User:
    return await users.confirm_email(data.token)


@router.post("/phone/request", status_code=202)
@inject
async def request_phone(
    authorization: AuthorizationHeader,
    auth: FromDishka[AuthService],
    users: FromDishka[UserService],
) -> dict[str, str]:
    user = await current_user(authorization, auth)
    await users.request_phone_verification(user.id)
    return {"status": "accepted"}


@router.post("/phone/confirm", response_model=UserResponse)
@inject
async def confirm_phone(
    data: VerificationTokenRequest,
    authorization: AuthorizationHeader,
    auth: FromDishka[AuthService],
    users: FromDishka[UserService],
) -> User:
    user = await current_user(authorization, auth)
    return await users.confirm_phone(user.id, data.token)


@router.post("/telegram/request", response_model=TelegramLinkResponse)
@inject
async def request_telegram(
    authorization: AuthorizationHeader,
    auth: FromDishka[AuthService],
    users: FromDishka[UserService],
    settings: FromDishka[Settings],
) -> TelegramLinkResponse:
    user = await current_user(authorization, auth)
    token = await users.request_telegram_verification(user.id)
    return TelegramLinkResponse(
        deep_link=f"https://t.me/{settings.telegram_bot_username}?start={token}"
    )
