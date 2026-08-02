from uuid import UUID

from app.domain.users.models import UserRole
from app.models import CommandModel


class CreateUser(CommandModel):
    email: str
    password: str
    phone: str | None = None
    username: str | None = None
    role: UserRole = "user"
    name: str = ""
    surname: str = ""
    patronymic: str | None = None
    telegram_username: str | None = None
    comment: str | None = None
    avatar_image: str | None = None
    header_image: str | None = None
    is_superuser: bool = False
    created_by: UUID | None = None


class UpdateUser(CommandModel):
    email: str | None = None
    phone: str | None = None
    username: str | None = None
    role: UserRole | None = None
    is_active: bool | None = None
    name: str | None = None
    surname: str | None = None
    patronymic: str | None = None
    telegram_username: str | None = None
    comment: str | None = None
    avatar_image: str | None = None
    header_image: str | None = None
    is_superuser: bool | None = None
    password: str | None = None
    clear_fields: frozenset[str] = frozenset()


class AccessToken(CommandModel):
    access_token: str
    token_type: str = "bearer"
