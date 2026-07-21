from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class CreateUser:
    email: str
    password: str
    phone: str | None = None
    name: str = ""
    surname: str = ""
    patronymic: str | None = None
    telegram_username: str | None = None
    comment: str | None = None
    avatar_image: str | None = None
    header_image: str | None = None
    is_superuser: bool = False
    created_by: UUID | None = None


@dataclass(frozen=True, slots=True)
class UpdateUser:
    email: str | None = None
    phone: str | None = None
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


@dataclass(frozen=True, slots=True)
class AccessToken:
    access_token: str
    token_type: str = "bearer"
