from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4


@dataclass(slots=True)
class User:
    email: str
    password_hash: str
    id: UUID = field(default_factory=uuid4)
    phone: str | None = None
    telegram_id: int | None = None
    telegram_username: str | None = None
    is_active: bool = True
    is_superuser: bool = False
    is_email_verified: bool = False
    is_phone_verified: bool = False
    email_verification_token_hash: str | None = None
    phone_verification_token_hash: str | None = None
    telegram_verification_token_hash: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
