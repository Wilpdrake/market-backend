from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    phone: str | None = Field(default=None, max_length=32)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UpdateUserRequest(BaseModel):
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=32)
    is_active: bool | None = None


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: EmailStr
    phone: str | None
    telegram_id: int | None
    telegram_username: str | None
    is_active: bool
    is_superuser: bool
    is_email_verified: bool
    is_phone_verified: bool
    created_at: datetime
    updated_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    token_type: str


class VerificationTokenRequest(BaseModel):
    token: str


class TelegramLinkResponse(BaseModel):
    deep_link: str


class TelegramUser(BaseModel):
    id: int
    username: str | None = None


class TelegramChat(BaseModel):
    id: int


class TelegramMessage(BaseModel):
    text: str | None = None
    chat: TelegramChat
    from_user: TelegramUser | None = Field(default=None, alias="from")


class TelegramUpdate(BaseModel):
    message: TelegramMessage | None = None
