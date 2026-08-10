from collections.abc import AsyncIterator
from urllib.parse import urlsplit

from dishka import AsyncContainer, Provider, Scope, make_async_container, provide
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine

from app.application.audit.ports import AuditRepository
from app.application.audit.services import AuditService
from app.application.orders.ports import OrderRepository
from app.application.orders.services import OrderService
from app.application.payments.ports import PaymentGateway, PaymentRepository
from app.application.payments.services import PaymentService
from app.application.products.ports import ProductRepository
from app.application.products.services import ProductService
from app.application.tags.ports import TagRepository
from app.application.tags.services import TagService
from app.application.users.ports import (
    AccessTokenService,
    PasswordHasher,
    UserRepository,
    VerificationNotifier,
)
from app.application.users.services import AuthService, UserService
from app.core.config import Settings, get_settings
from app.infrastructure.database.audit_repositories import SqlAlchemyAuditRepository
from app.infrastructure.database.order_repositories import SqlAlchemyOrderRepository
from app.infrastructure.database.payment_repositories import SqlAlchemyPaymentRepository
from app.infrastructure.database.product_repositories import SqlAlchemyProductRepository
from app.infrastructure.database.repositories import SqlAlchemyUserRepository
from app.infrastructure.database.tag_repositories import SqlAlchemyTagRepository
from app.infrastructure.notifications import LoggingVerificationNotifier
from app.infrastructure.payments.tbank import (
    StubPaymentGateway,
    TBankPaymentGateway,
    default_payment_options,
)
from app.infrastructure.security.passwords import Argon2PasswordHasher
from app.infrastructure.security.tokens import JwtTokenService


class AppProvider(Provider):
    @provide(scope=Scope.APP)
    def settings(self) -> Settings:
        return get_settings()

    @provide(scope=Scope.APP)
    def engine(self, settings: Settings) -> AsyncEngine:
        return create_async_engine(settings.resolved_database_url, pool_pre_ping=True)

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

    @provide(scope=Scope.REQUEST, provides=TagRepository)
    def tag_repository(self, session: AsyncSession) -> SqlAlchemyTagRepository:
        return SqlAlchemyTagRepository(session)

    @provide(scope=Scope.REQUEST, provides=AuditRepository)
    def audit_repository(self, session: AsyncSession) -> SqlAlchemyAuditRepository:
        return SqlAlchemyAuditRepository(session)

    @provide(scope=Scope.REQUEST, provides=OrderRepository)
    def order_repository(self, session: AsyncSession) -> SqlAlchemyOrderRepository:
        return SqlAlchemyOrderRepository(session)

    @provide(scope=Scope.REQUEST, provides=PaymentRepository)
    def payment_repository(self, session: AsyncSession) -> SqlAlchemyPaymentRepository:
        return SqlAlchemyPaymentRepository(session)

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

    @provide(scope=Scope.APP, provides=PaymentGateway)
    def payment_gateway(self, settings: Settings) -> PaymentGateway:
        """Use T-Bank in production and a deterministic stub only outside production."""
        options = default_payment_options()
        if not settings.tbank_is_configured:
            if settings.environment == "production":
                raise RuntimeError(
                    "TBANK_TERMINAL_KEY and TBANK_PASSWORD are required in production"
                )
            return StubPaymentGateway(options)
        if settings.environment == "production":
            notification = urlsplit(settings.tbank_notification_url or "")
            if notification.scheme != "https" or not notification.hostname:
                raise RuntimeError(
                    "TBANK_NOTIFICATION_URL must be a public HTTPS URL in production"
                )
        return TBankPaymentGateway(
            terminal_key=settings.tbank_terminal_key or "",
            password=settings.tbank_password or "",
            options=options,
            api_url=settings.tbank_api_url,
            success_url=settings.tbank_success_url,
            fail_url=settings.tbank_fail_url,
            notification_url=settings.tbank_notification_url,
        )

    user_service = provide(UserService, scope=Scope.REQUEST)
    auth_service = provide(AuthService, scope=Scope.REQUEST)

    @provide(scope=Scope.REQUEST)
    def product_service(self, repository: ProductRepository, tags: TagRepository) -> ProductService:
        return ProductService(repository, tags)

    tag_service = provide(TagService, scope=Scope.REQUEST)
    audit_service = provide(AuditService, scope=Scope.REQUEST)
    order_service = provide(OrderService, scope=Scope.REQUEST)
    payment_service = provide(PaymentService, scope=Scope.REQUEST)


def create_container() -> AsyncContainer:
    return make_async_container(AppProvider())
