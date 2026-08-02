from datetime import datetime
from uuid import UUID

from pydantic import EmailStr, Field

from app.domain.users.models import UserRole
from app.models import ApiModel, ApiResponseModel


class RegisterRequest(ApiModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    phone: str | None = Field(default=None, max_length=32)


class LoginRequest(ApiModel):
    # The historical JSON key remains ``email`` for API compatibility, but the value may
    # now be either an email address or the human-friendly username from deployment data.
    email: str = Field(min_length=1, max_length=320)
    password: str = Field(min_length=8, max_length=128)


class UpdateUserRequest(ApiModel):
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=32)
    is_active: bool | None = None


class UserResponse(ApiResponseModel):
    id: UUID
    username: str | None
    email: EmailStr
    phone: str | None
    telegram_id: int | None
    telegram_username: str | None
    is_active: bool
    is_superuser: bool
    role: UserRole
    is_email_verified: bool
    is_phone_verified: bool
    created_at: datetime
    updated_at: datetime


class TokenResponse(ApiModel):
    access_token: str
    token_type: str


class VerificationTokenRequest(ApiModel):
    token: str


class TelegramLinkResponse(ApiModel):
    deep_link: str


class TelegramUser(ApiModel):
    id: int
    username: str | None = None


class TelegramChat(ApiModel):
    id: int


class TelegramMessage(ApiModel):
    text: str | None = None
    chat: TelegramChat
    from_user: TelegramUser | None = Field(default=None, alias="from")


class TelegramUpdate(ApiModel):
    message: TelegramMessage | None = None
