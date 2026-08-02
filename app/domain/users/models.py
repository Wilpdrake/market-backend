import re
from datetime import UTC, datetime
from typing import Literal
from uuid import UUID, uuid4

from pydantic import Field

from app.models import EntityModel

# Roles are domain data, not frontend labels. Keep this union close to the User model so
# HTTP schemas, services and persistence all share the same allowed values.
UserRole = Literal["user", "moder", "admin", "developer", "owner"]
ADMIN_ROLES: frozenset[str] = frozenset({"moder", "admin", "developer", "owner"})
ROLE_RANK: dict[UserRole, int] = {
    "user": 0,
    "moder": 1,
    "admin": 2,
    "owner": 3,
    "developer": 4,
}
# Email addresses always contain ``@``. Excluding it makes email and username disjoint
# namespaces that PostgreSQL can enforce atomically with ordinary unique constraints.
_USERNAME_PATTERN = re.compile(r"^[a-z0-9._+-]+$")


def normalize_username(value: str) -> str:
    normalized = value.strip().lower()
    if not _USERNAME_PATTERN.fullmatch(normalized):
        raise ValueError("Username contains unsupported characters")
    return normalized


class User(EntityModel):
    email: str
    password_hash: str
    id: UUID = Field(default_factory=uuid4)
    phone: str | None = None
    username: str | None = None
    role: UserRole = "user"
    name: str = ""
    surname: str = ""
    patronymic: str | None = None
    comment: str | None = None
    avatar_image: str | None = None
    header_image: str | None = None
    created_by: UUID | None = None
    telegram_id: int | None = None
    telegram_username: str | None = None
    is_active: bool = True
    is_superuser: bool = False
    is_email_verified: bool = False
    is_phone_verified: bool = False
    email_verification_token_hash: str | None = None
    phone_verification_token_hash: str | None = None
    telegram_verification_token_hash: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @property
    def effective_role(self) -> UserRole:
        """Treat legacy boolean superusers as administrators until persisted roles catch up."""
        if self.is_superuser and ROLE_RANK[self.role] < ROLE_RANK["admin"]:
            return "admin"
        return self.role
