from collections.abc import AsyncIterator

from dishka import AsyncContainer, Provider, Scope, make_async_container, provide
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine

from app.application.products.ports import ProductRepository
from app.application.products.services import ProductService
from app.application.users.ports import (
    AccessTokenService,
    PasswordHasher,
    UserRepository,
    VerificationNotifier,
)
from app.application.users.services import AuthService, UserService
from app.core.config import Settings, get_settings
from app.infrastructure.database.product_repositories import SqlAlchemyProductRepository
from app.infrastructure.database.repositories import SqlAlchemyUserRepository
from app.infrastructure.notifications import LoggingVerificationNotifier
from app.infrastructure.security.passwords import Argon2PasswordHasher
from app.infrastructure.security.tokens import JwtTokenService


class AppProvider(Provider):
    @provide(scope=Scope.APP)
    def settings(self) -> Settings:
        return get_settings()

    @provide(scope=Scope.APP)
    def engine(self, settings: Settings) -> AsyncEngine:
        return create_async_engine(settings.database_url, pool_pre_ping=True)

    @provide(scope=Scope.REQUEST)
    async def session(self, engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
        async with AsyncSession(engine, expire_on_commit=False) as session:
            yield session

    @provide(scope=Scope.REQUEST, provides=UserRepository)
    def user_repository(self, session: AsyncSession) -> SqlAlchemyUserRepository:
        return SqlAlchemyUserRepository(session)

    @provide(scope=Scope.REQUEST, provides=ProductRepository)
    def product_repository(self, session: AsyncSession) -> SqlAlchemyProductRepository:
        return SqlAlchemyProductRepository(session)

    @provide(scope=Scope.APP, provides=PasswordHasher)
    def password_hasher(self) -> Argon2PasswordHasher:
        return Argon2PasswordHasher()

    @provide(scope=Scope.APP, provides=AccessTokenService)
    def token_service(self, settings: Settings) -> JwtTokenService:
        return JwtTokenService(
            secret_key=settings.secret_key,
            expires_minutes=settings.access_token_expire_minutes,
        )

    @provide(scope=Scope.APP, provides=VerificationNotifier)
    def notifier(self, settings: Settings) -> LoggingVerificationNotifier:
        return LoggingVerificationNotifier(expose_tokens=settings.environment == "development")

    user_service = provide(UserService, scope=Scope.REQUEST)
    auth_service = provide(AuthService, scope=Scope.REQUEST)
    product_service = provide(ProductService, scope=Scope.REQUEST)


def create_container() -> AsyncContainer:
    return make_async_container(AppProvider())
