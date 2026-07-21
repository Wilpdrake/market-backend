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
    PermissionDeniedError,
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
            name=data.name,
            surname=data.surname,
            patronymic=data.patronymic,
            telegram_username=data.telegram_username,
            comment=data.comment,
            avatar_image=data.avatar_image,
            header_image=data.header_image,
            is_superuser=data.is_superuser,
            created_by=data.created_by,
        )
        return await self.repository.add(user)

    async def get(self, user_id: UUID) -> User:
        user = await self.repository.get_by_id(user_id)
        if user is None:
            raise NotFoundError("User not found")
        return user

    async def list(self, *, offset: int = 0, limit: int = 100) -> list[User]:
        return await self.repository.list(offset=offset, limit=limit)

    async def get_by_email(self, email: str) -> User | None:
        return await self.repository.get_by_email(email.strip().lower())

    async def update(self, user_id: UUID, data: UpdateUser) -> User:
        user = await self.get(user_id)
        email = data.email.strip().lower() if data.email is not None else user.email
        owner = await self.repository.get_by_email(email)
        if owner is not None and owner.id != user_id:
            raise ConflictError("A user with this email already exists")
        email_changed = email != user.email
        new_phone = None if "phone" in data.clear_fields else data.phone
        phone_was_supplied = data.phone is not None or "phone" in data.clear_fields
        phone_changed = phone_was_supplied and new_phone != user.phone
        updated = replace(
            user,
            email=email,
            phone=new_phone if phone_was_supplied else user.phone,
            is_active=data.is_active if data.is_active is not None else user.is_active,
            name=data.name if data.name is not None else user.name,
            surname=data.surname if data.surname is not None else user.surname,
            patronymic=(
                None
                if "patronymic" in data.clear_fields
                else data.patronymic
                if data.patronymic is not None
                else user.patronymic
            ),
            telegram_username=(
                None
                if "telegram_username" in data.clear_fields
                else data.telegram_username
                if data.telegram_username is not None
                else user.telegram_username
            ),
            comment=(
                None
                if "comment" in data.clear_fields
                else data.comment
                if data.comment is not None
                else user.comment
            ),
            avatar_image=(
                None
                if "avatar_image" in data.clear_fields
                else data.avatar_image
                if data.avatar_image is not None
                else user.avatar_image
            ),
            header_image=(
                None
                if "header_image" in data.clear_fields
                else data.header_image
                if data.header_image is not None
                else user.header_image
            ),
            is_superuser=(
                data.is_superuser if data.is_superuser is not None else user.is_superuser
            ),
            password_hash=(
                self.password_hasher.hash(data.password)
                if data.password is not None
                else user.password_hash
            ),
            is_email_verified=False if email_changed else user.is_email_verified,
            email_verification_token_hash=(
                None if email_changed else user.email_verification_token_hash
            ),
            is_phone_verified=False if phone_changed else user.is_phone_verified,
            phone_verification_token_hash=(
                None if phone_changed else user.phone_verification_token_hash
            ),
            updated_at=datetime.now(UTC),
        )
        return await self.repository.save(updated)

    async def delete(self, user_id: UUID, *, actor: User | None = None) -> None:
        if actor is not None and actor.id == user_id and actor.is_superuser:
            raise PermissionDeniedError("An administrator cannot delete their own account")
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

    async def admin_login(self, email: str, password: str) -> AccessToken:
        user = await self.repository.get_by_email(email.strip().lower())
        if (
            user is None
            or not user.is_superuser
            or not user.is_active
            or not self.password_hasher.verify(password, user.password_hash)
        ):
            raise InvalidCredentialsError("Invalid administrator credentials")
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
