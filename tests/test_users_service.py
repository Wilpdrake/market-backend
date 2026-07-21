from uuid import UUID

import pytest

from app.application.users.dto import CreateUser, UpdateUser
from app.application.users.exceptions import ConflictError, InvalidCredentialsError
from app.application.users.services import AuthService, UserService
from app.domain.users.entities import User


class InMemoryUserRepository:
    def __init__(self) -> None:
        self.users: dict[UUID, User] = {}

    async def add(self, user: User) -> User:
        self.users[user.id] = user
        return user

    async def get_by_id(self, user_id: UUID) -> User | None:
        return self.users.get(user_id)

    async def get_by_email(self, email: str) -> User | None:
        return next((user for user in self.users.values() if user.email == email), None)

    async def list(self, *, offset: int, limit: int) -> list[User]:
        return list(self.users.values())[offset : offset + limit]

    async def save(self, user: User) -> User:
        self.users[user.id] = user
        return user

    async def delete(self, user_id: UUID) -> None:
        self.users.pop(user_id, None)


class FakeNotifier:
    def __init__(self) -> None:
        self.email_tokens: list[tuple[str, str]] = []
        self.phone_tokens: list[tuple[str, str]] = []

    async def send_email_verification(self, email: str, token: str) -> None:
        self.email_tokens.append((email, token))

    async def send_phone_verification(self, phone: str, token: str) -> None:
        self.phone_tokens.append((phone, token))


@pytest.fixture
def services() -> tuple[UserService, AuthService, InMemoryUserRepository, FakeNotifier]:
    from app.infrastructure.security.passwords import Argon2PasswordHasher
    from app.infrastructure.security.tokens import JwtTokenService

    repository = InMemoryUserRepository()
    notifier = FakeNotifier()
    password_hasher = Argon2PasswordHasher()
    users = UserService(repository, password_hasher, notifier)
    auth = AuthService(
        repository,
        password_hasher,
        JwtTokenService(secret_key="test-secret-with-at-least-32-bytes"),
    )
    return users, auth, repository, notifier


async def test_register_hashes_password_and_rejects_duplicate_email(services) -> None:
    users, _, _, _ = services

    created = await users.create(
        CreateUser(email="User@Example.com", password="a-strong-password", phone="+79991234567")
    )

    assert created.email == "user@example.com"
    assert created.password_hash != "a-strong-password"
    with pytest.raises(ConflictError):
        await users.create(CreateUser(email="user@example.com", password="another-password"))


async def test_authenticate_returns_token_for_valid_credentials(services) -> None:
    users, auth, _, _ = services
    created = await users.create(CreateUser(email="user@example.com", password="a-strong-password"))

    token = await auth.login("user@example.com", "a-strong-password")

    assert await auth.get_current_user(token.access_token) == created
    with pytest.raises(InvalidCredentialsError):
        await auth.login("user@example.com", "wrong-password")


async def test_email_confirmation_accepts_only_issued_token(services) -> None:
    users, _, repository, notifier = services
    created = await users.create(CreateUser(email="user@example.com", password="a-strong-password"))

    await users.request_email_verification(created.id)
    _, token = notifier.email_tokens[-1]
    confirmed = await users.confirm_email(token)

    assert confirmed.is_email_verified is True
    assert repository.users[created.id].email_verification_token_hash is None


async def test_update_and_delete_user(services) -> None:
    users, _, repository, _ = services
    created = await users.create(CreateUser(email="user@example.com", password="a-strong-password"))

    updated = await users.update(created.id, UpdateUser(phone="+79990000000"))
    await users.delete(updated.id)

    assert updated.phone == "+79990000000"
    assert updated.id not in repository.users


async def test_telegram_account_is_bound_with_one_time_token(services) -> None:
    users, _, _, _ = services
    created = await users.create(CreateUser(email="user@example.com", password="a-strong-password"))

    token = await users.request_telegram_verification(created.id)
    confirmed = await users.confirm_telegram(token, 123456, "market_user")

    assert confirmed.telegram_id == 123456
    assert confirmed.telegram_username == "market_user"
    assert confirmed.telegram_verification_token_hash is None
