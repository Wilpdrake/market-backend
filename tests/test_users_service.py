from dataclasses import replace
from uuid import UUID

import pytest

from app.application.users.dto import CreateUser, UpdateUser
from app.application.users.exceptions import (
    ConflictError,
    InvalidCredentialsError,
    PermissionDeniedError,
)
from app.application.users.services import AuthService, UserService
from app.domain.users.entities import User
from app.presentation.api.v1.admin.dependencies import current_admin


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

    async def get_by_login(self, login: str) -> User | None:
        return next(
            (user for user in self.users.values() if user.email == login or user.username == login),
            None,
        )

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


type ServiceBundle = tuple[UserService, AuthService, InMemoryUserRepository, FakeNotifier]


@pytest.fixture
def services() -> ServiceBundle:
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


async def test_register_hashes_password_and_rejects_duplicate_email(
    services: ServiceBundle,
) -> None:
    users, _, _, _ = services

    created = await users.create(
        CreateUser(email="User@Example.com", password="a-strong-password", phone="+79991234567")
    )

    assert created.email == "user@example.com"
    assert created.password_hash != "a-strong-password"
    with pytest.raises(ConflictError):
        await users.create(CreateUser(email="user@example.com", password="another-password"))


async def test_authenticate_returns_token_for_valid_credentials(services: ServiceBundle) -> None:
    users, auth, _, _ = services
    created = await users.create(CreateUser(email="user@example.com", password="a-strong-password"))

    token = await auth.login("user@example.com", "a-strong-password")

    assert await auth.get_current_user(token.access_token) == created
    with pytest.raises(InvalidCredentialsError):
        await auth.login("user@example.com", "wrong-password")


async def test_email_confirmation_accepts_only_issued_token(services: ServiceBundle) -> None:
    users, _, repository, notifier = services
    created = await users.create(CreateUser(email="user@example.com", password="a-strong-password"))

    await users.request_email_verification(created.id)
    _, token = notifier.email_tokens[-1]
    confirmed = await users.confirm_email(token)

    assert confirmed.is_email_verified is True
    assert repository.users[created.id].email_verification_token_hash is None


async def test_admin_login_rejects_regular_user(services: ServiceBundle) -> None:
    users, auth, repository, _ = services
    regular = await users.create(
        CreateUser(email="admin@example.com", password="a-strong-password")
    )

    with pytest.raises(InvalidCredentialsError):
        await auth.admin_login(regular.email, "a-strong-password")

    repository.users[regular.id] = replace(regular, is_superuser=True)
    token = await auth.admin_login(regular.email, "a-strong-password")

    assert token.token_type == "bearer"


async def test_owner_can_sign_in_with_username_and_keeps_explicit_role(
    services: ServiceBundle,
) -> None:
    users, auth, _, _ = services
    owner = await users.create(
        CreateUser(
            email="owner@example.com",
            username="owner-login",
            password="a-strong-password",
            role="owner",
        )
    )

    token = await auth.login("owner-login", "a-strong-password")

    assert owner.role == "owner"
    assert owner.is_superuser is True
    assert await auth.get_current_user(token.access_token) == owner


async def test_login_identifiers_share_one_namespace(services: ServiceBundle) -> None:
    users, _, _, _ = services

    with pytest.raises(ConflictError):
        await users.create(
            CreateUser(
                email="first@example.com",
                username="shared@example.com",
                password="a-strong-password",
            )
        )


async def test_username_must_not_normalize_to_empty(services: ServiceBundle) -> None:
    users, _, _, _ = services

    with pytest.raises(ConflictError):
        await users.create(
            CreateUser(
                email="blank@example.com",
                username="   ",
                password="a-strong-password",
            )
        )


async def test_administrator_cannot_assign_or_manage_equal_or_higher_role(
    services: ServiceBundle,
) -> None:
    users, _, _, _ = services
    moderator = await users.create(
        CreateUser(email="moder@example.com", password="a-strong-password", role="moder")
    )
    administrator = await users.create(
        CreateUser(email="admin@example.com", password="a-strong-password", role="admin")
    )
    regular = await users.create(
        CreateUser(email="user@example.com", password="a-strong-password")
    )

    with pytest.raises(PermissionDeniedError):
        await users.create(
            CreateUser(email="owner@example.com", password="a-strong-password", role="owner"),
            actor=moderator,
        )
    with pytest.raises(PermissionDeniedError):
        await users.delete(administrator.id, actor=moderator)
    with pytest.raises(PermissionDeniedError):
        await users.update(regular.id, UpdateUser(is_superuser=True), actor=moderator)


async def test_legacy_superuser_uses_admin_rank_and_is_normalized_on_update(
    services: ServiceBundle,
) -> None:
    users, _, repository, _ = services
    moderator = await users.create(
        CreateUser(email="moder@example.com", password="a-strong-password", role="moder")
    )
    owner = await users.create(
        CreateUser(email="owner@example.com", password="a-strong-password", role="owner")
    )
    legacy = await users.create(
        CreateUser(email="legacy@example.com", password="a-strong-password")
    )
    repository.users[legacy.id] = replace(legacy, is_superuser=True)

    with pytest.raises(PermissionDeniedError):
        await users.update(legacy.id, UpdateUser(name="Compromised"), actor=moderator)

    unchanged = repository.users[legacy.id]
    assert unchanged.name == ""
    assert unchanged.role == "user"
    assert unchanged.is_superuser is True

    normalized = await users.update(legacy.id, UpdateUser(name="Legacy Admin"), actor=owner)

    assert normalized.name == "Legacy Admin"
    assert normalized.role == "admin"
    assert normalized.is_superuser is True


async def test_admin_dependency_rejects_regular_user_token(services: ServiceBundle) -> None:
    users, auth, _, _ = services
    await users.create(CreateUser(email="user@example.com", password="a-strong-password"))
    token = await auth.login("user@example.com", "a-strong-password")

    with pytest.raises(PermissionDeniedError):
        await current_admin(f"Bearer {token.access_token}", auth)


async def test_administrator_cannot_delete_self_through_user_service(
    services: ServiceBundle,
) -> None:
    users, _, repository, _ = services
    created = await users.create(
        CreateUser(
            email="admin@example.com",
            password="a-strong-password",
            is_superuser=True,
        )
    )

    with pytest.raises(PermissionDeniedError):
        await users.delete(created.id, actor=created)

    assert created.id in repository.users


async def test_regular_user_can_delete_their_own_account(services: ServiceBundle) -> None:
    users, _, repository, _ = services
    created = await users.create(CreateUser(email="user@example.com", password="a-strong-password"))

    await users.delete(created.id, actor=created)

    assert created.id not in repository.users


async def test_update_and_delete_user(services: ServiceBundle) -> None:
    users, _, repository, _ = services
    created = await users.create(CreateUser(email="user@example.com", password="a-strong-password"))

    updated = await users.update(created.id, UpdateUser(phone="+79990000000"))
    await users.delete(updated.id)

    assert updated.phone == "+79990000000"
    assert updated.id not in repository.users


async def test_changing_contact_resets_verification(services: ServiceBundle) -> None:
    users, _, repository, _ = services
    created = await users.create(
        CreateUser(
            email="old@example.com",
            password="a-strong-password",
            phone="+79990000000",
        )
    )
    repository.users[created.id] = replace(
        created,
        is_email_verified=True,
        is_phone_verified=True,
        email_verification_token_hash="old-email-token",
        phone_verification_token_hash="old-phone-token",
    )

    updated = await users.update(
        created.id,
        UpdateUser(
            email="new@example.com",
            clear_fields=frozenset({"phone"}),
        ),
    )

    assert updated.is_email_verified is False
    assert updated.is_phone_verified is False
    assert updated.email_verification_token_hash is None
    assert updated.phone_verification_token_hash is None
    assert updated.phone is None


async def test_telegram_account_is_bound_with_one_time_token(services: ServiceBundle) -> None:
    users, _, _, _ = services
    created = await users.create(CreateUser(email="user@example.com", password="a-strong-password"))

    token = await users.request_telegram_verification(created.id)
    confirmed = await users.confirm_telegram(token, 123456, "market_user")

    assert confirmed.telegram_id == 123456
    assert confirmed.telegram_username == "market_user"
    assert confirmed.telegram_verification_token_hash is None
