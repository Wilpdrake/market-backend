import hashlib
import secrets
from dataclasses import replace
from datetime import UTC, datetime
from uuid import UUID

from app.application.users.dto import AccessToken, CreateUser, UpdateUser
from app.application.users.exceptions import (
    ConflictError,
    InvalidCredentialsError,
    InvalidVerificationTokenError,
    NotFoundError,
)
from app.application.users.ports import (
    AccessTokenService,
    PasswordHasher,
    UserRepository,
    VerificationNotifier,
)
from app.domain.users.entities import User


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


class UserService:
    def __init__(
        self,
        repository: UserRepository,
        password_hasher: PasswordHasher,
        notifier: VerificationNotifier,
    ) -> None:
        self.repository = repository
        self.password_hasher = password_hasher
        self.notifier = notifier

    async def create(self, data: CreateUser) -> User:
        email = data.email.strip().lower()
        if await self.repository.get_by_email(email):
            raise ConflictError("A user with this email already exists")
        user = User(
            email=email,
            password_hash=self.password_hasher.hash(data.password),
            phone=data.phone,
        )
        return await self.repository.add(user)

    async def get(self, user_id: UUID) -> User:
        user = await self.repository.get_by_id(user_id)
        if user is None:
            raise NotFoundError("User not found")
        return user

    async def list(self, *, offset: int = 0, limit: int = 100) -> list[User]:
        return await self.repository.list(offset=offset, limit=limit)

    async def update(self, user_id: UUID, data: UpdateUser) -> User:
        user = await self.get(user_id)
        email = data.email.strip().lower() if data.email is not None else user.email
        owner = await self.repository.get_by_email(email)
        if owner is not None and owner.id != user_id:
            raise ConflictError("A user with this email already exists")
        updated = replace(
            user,
            email=email,
            phone=data.phone if data.phone is not None else user.phone,
            is_active=data.is_active if data.is_active is not None else user.is_active,
            updated_at=datetime.now(UTC),
        )
        return await self.repository.save(updated)

    async def delete(self, user_id: UUID) -> None:
        await self.get(user_id)
        await self.repository.delete(user_id)

    async def request_email_verification(self, user_id: UUID) -> None:
        user = await self.get(user_id)
        token = secrets.token_urlsafe(32)
        await self.repository.save(replace(user, email_verification_token_hash=_token_hash(token)))
        await self.notifier.send_email_verification(user.email, token)

    async def request_phone_verification(self, user_id: UUID) -> None:
        user = await self.get(user_id)
        if user.phone is None:
            raise ConflictError("A phone number is required")
        token = f"{secrets.randbelow(1_000_000):06d}"
        await self.repository.save(replace(user, phone_verification_token_hash=_token_hash(token)))
        await self.notifier.send_phone_verification(user.phone, token)

    async def confirm_email(self, token: str) -> User:
        expected_hash = _token_hash(token)
        users = await self.repository.list(offset=0, limit=10_000)
        user = next(
            (item for item in users if item.email_verification_token_hash == expected_hash),
            None,
        )
        if user is None:
            raise InvalidVerificationTokenError("Invalid email verification token")
        return await self.repository.save(
            replace(user, is_email_verified=True, email_verification_token_hash=None)
        )

    async def confirm_phone(self, user_id: UUID, token: str) -> User:
        user = await self.get(user_id)
        if not secrets.compare_digest(user.phone_verification_token_hash or "", _token_hash(token)):
            raise InvalidVerificationTokenError("Invalid phone verification token")
        return await self.repository.save(
            replace(user, is_phone_verified=True, phone_verification_token_hash=None)
        )

    async def request_telegram_verification(self, user_id: UUID) -> str:
        user = await self.get(user_id)
        token = secrets.token_urlsafe(24)
        await self.repository.save(
            replace(user, telegram_verification_token_hash=_token_hash(token))
        )
        return token

    async def confirm_telegram(
        self,
        token: str,
        telegram_id: int,
        telegram_username: str | None,
    ) -> User:
        expected_hash = _token_hash(token)
        users = await self.repository.list(offset=0, limit=10_000)
        user = next(
            (item for item in users if item.telegram_verification_token_hash == expected_hash),
            None,
        )
        if user is None:
            raise InvalidVerificationTokenError("Invalid Telegram verification token")
        return await self.repository.save(
            replace(
                user,
                telegram_id=telegram_id,
                telegram_username=telegram_username,
                telegram_verification_token_hash=None,
            )
        )


class AuthService:
    def __init__(
        self,
        repository: UserRepository,
        password_hasher: PasswordHasher,
        token_service: AccessTokenService,
    ) -> None:
        self.repository = repository
        self.password_hasher = password_hasher
        self.token_service = token_service

    async def login(self, email: str, password: str) -> AccessToken:
        user = await self.repository.get_by_email(email.strip().lower())
        if user is None or not self.password_hasher.verify(password, user.password_hash):
            raise InvalidCredentialsError("Invalid email or password")
        if not user.is_active:
            raise InvalidCredentialsError("User is inactive")
        return AccessToken(access_token=self.token_service.create(user.id))

    async def get_current_user(self, token: str) -> User:
        try:
            user_id = self.token_service.decode(token)
        except ValueError as error:
            raise InvalidCredentialsError("Invalid access token") from error
        user = await self.repository.get_by_id(user_id)
        if user is None or not user.is_active:
            raise InvalidCredentialsError("Invalid access token")
        return user
