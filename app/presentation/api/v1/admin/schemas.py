from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import ConfigDict, EmailStr, Field, model_validator

from app.domain.orders.models import CrmStatus, Order
from app.domain.users.models import UserRole
from app.models import ApiModel, ApiResponseModel


class AdminLoginRequest(ApiModel):
    email: str = Field(min_length=1, max_length=320)
    password: str = Field(min_length=8, max_length=128)


class AdminUserCreateRequest(ApiModel):
    name: str = Field(min_length=1, max_length=100)
    surname: str = Field(min_length=1, max_length=100)
    patronymic: str | None = Field(default=None, max_length=100)
    username: str | None = Field(default=None, min_length=1, max_length=64)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    password_confirmation: str = Field(min_length=8, max_length=128)
    contact_number: str | None = Field(default=None, max_length=32)
    telegram_username: str | None = Field(default=None, max_length=64)
    comment: str | None = Field(default=None, max_length=2000)
    avatar_image: str | None = Field(default=None, max_length=2048)
    header_image: str | None = Field(default=None, max_length=2048)
    role: UserRole = "user"

    @model_validator(mode="after")
    def passwords_match(self) -> "AdminUserCreateRequest":
        if self.password != self.password_confirmation:
            raise ValueError("Passwords do not match")
        return self


class AdminUserUpdateRequest(ApiModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    surname: str | None = Field(default=None, min_length=1, max_length=100)
    patronymic: str | None = Field(default=None, max_length=100)
    username: str | None = Field(default=None, min_length=1, max_length=64)
    email: EmailStr | None = None
    password: str | None = Field(default=None, min_length=8, max_length=128)
    password_confirmation: str | None = Field(default=None, min_length=8, max_length=128)
    contact_number: str | None = Field(default=None, max_length=32)
    telegram_username: str | None = Field(default=None, max_length=64)
    comment: str | None = Field(default=None, max_length=2000)
    avatar_image: str | None = Field(default=None, max_length=2048)
    header_image: str | None = Field(default=None, max_length=2048)
    role: UserRole | None = None
    is_active: bool | None = None

    @model_validator(mode="after")
    def passwords_match(self) -> "AdminUserUpdateRequest":
        if self.password != self.password_confirmation:
            raise ValueError("Passwords do not match")
        return self


class AdminUserResponse(ApiResponseModel):
    model_config = ConfigDict(populate_by_name=True)

    uuid: UUID = Field(validation_alias="id")
    name: str
    surname: str
    patronymic: str | None
    username: str | None
    email: EmailStr
    contact_number: str | None = Field(validation_alias="phone")
    telegram_username: str | None
    comment: str | None
    avatar_image: str | None
    header_image: str | None
    role: UserRole
    is_superuser: bool
    created_by: UUID | None
    is_active: bool
    is_email_verified: bool
    is_phone_verified: bool
    created_at: datetime
    updated_at: datetime


class TagSummary(ApiResponseModel):
    model_config = ConfigDict(populate_by_name=True)

    uuid: UUID = Field(validation_alias="id")
    name: str
    slug: str


class TagResponse(TagSummary):
    description: str | None
    created_at: datetime
    updated_at: datetime


class TagCreateRequest(ApiModel):
    name: str = Field(min_length=1, max_length=100)
    slug: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=2000)


class TagUpdateRequest(ApiModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    slug: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=2000)


class ProductRequest(ApiModel):
    pass


class ProductCreateRequest(ProductRequest):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=5000)
    images: list[str] | None = None
    header_image: str | None = Field(default=None, max_length=2048)
    price: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    ozon_price: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    wb_price: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    tag_ids: list[UUID] = Field(default_factory=list, max_length=100)


class ProductUpdateRequest(ProductRequest):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=5000)
    images: list[str] | None = None
    header_image: str | None = Field(default=None, max_length=2048)
    price: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    ozon_price: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    wb_price: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    tag_ids: list[UUID] | None = Field(default=None, max_length=100)


class ProductResponse(ApiResponseModel):
    model_config = ConfigDict(populate_by_name=True)

    uuid: UUID = Field(validation_alias="id")
    title: str
    description: str | None
    images: list[str] | None
    header_image: str | None
    price: Decimal | None
    ozon_price: Decimal | None
    wb_price: Decimal | None
    tags: list[TagSummary]
    created_by: UUID
    updated_by: UUID
    created_at: datetime
    updated_at: datetime


class CrmOrderResponse(ApiResponseModel):
    id: UUID
    customer_name: str
    customer_email: EmailStr
    total: Decimal
    status: CrmStatus
    created_at: datetime

    @classmethod
    def from_domain(cls, order: Order) -> "CrmOrderResponse":
        return cls(
            id=order.id,
            customer_name=order.customer.name,
            customer_email=order.customer.email,
            total=order.total,
            status=order.crm_status,
            created_at=order.created_at,
        )


class CrmOrderUpdateRequest(ApiModel):
    status: CrmStatus


class AuditLogResponse(ApiResponseModel):
    id: UUID
    admin_name: str
    admin_email: EmailStr
    action: str
    entity_type: str
    entity_id: str | None
    details: str | None
    created_at: datetime
    ip_address: str | None = None


class AuditLoggingSetting(ApiModel):
    enabled: bool
