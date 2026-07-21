from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator


class AdminLoginRequest(BaseModel):
    email: EmailStr
    password: str


class AdminUserCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    surname: str = Field(min_length=1, max_length=100)
    patronymic: str | None = Field(default=None, max_length=100)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    password_confirmation: str = Field(min_length=8, max_length=128)
    contact_number: str | None = Field(default=None, max_length=32)
    telegram_username: str | None = Field(default=None, max_length=64)
    comment: str | None = Field(default=None, max_length=2000)
    avatar_image: str | None = Field(default=None, max_length=2048)
    header_image: str | None = Field(default=None, max_length=2048)
    role: Literal["user", "admin"] = "user"

    @model_validator(mode="after")
    def passwords_match(self) -> "AdminUserCreateRequest":
        if self.password != self.password_confirmation:
            raise ValueError("Passwords do not match")
        return self


class AdminUserUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    surname: str | None = Field(default=None, min_length=1, max_length=100)
    patronymic: str | None = Field(default=None, max_length=100)
    email: EmailStr | None = None
    password: str | None = Field(default=None, min_length=8, max_length=128)
    password_confirmation: str | None = Field(default=None, min_length=8, max_length=128)
    contact_number: str | None = Field(default=None, max_length=32)
    telegram_username: str | None = Field(default=None, max_length=64)
    comment: str | None = Field(default=None, max_length=2000)
    avatar_image: str | None = Field(default=None, max_length=2048)
    header_image: str | None = Field(default=None, max_length=2048)
    role: Literal["user", "admin"] | None = None
    is_active: bool | None = None

    @model_validator(mode="after")
    def passwords_match(self) -> "AdminUserUpdateRequest":
        if self.password != self.password_confirmation:
            raise ValueError("Passwords do not match")
        return self


class AdminUserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    uuid: UUID = Field(validation_alias="id")
    name: str
    surname: str
    patronymic: str | None
    email: EmailStr
    contact_number: str | None = Field(validation_alias="phone")
    telegram_username: str | None
    comment: str | None
    avatar_image: str | None
    header_image: str | None
    role: str
    created_by: UUID | None
    is_active: bool
    is_email_verified: bool
    is_phone_verified: bool
    created_at: datetime
    updated_at: datetime


class ProductCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=5000)
    images: list[str] | None = None
    header_image: str | None = Field(default=None, max_length=2048)
    price: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    ozon_price: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    wb_price: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)


class ProductUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=5000)
    images: list[str] | None = None
    header_image: str | None = Field(default=None, max_length=2048)
    price: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    ozon_price: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    wb_price: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)


class ProductResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    uuid: UUID = Field(validation_alias="id")
    title: str
    description: str | None
    images: list[str] | None
    header_image: str | None
    price: Decimal | None
    ozon_price: Decimal | None
    wb_price: Decimal | None
    created_by: UUID
    updated_by: UUID
    created_at: datetime
    updated_at: datetime
