from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from dishka.integrations.fastapi import setup_dishka
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.application.payments.exceptions import PaymentProviderError
from app.application.users.exceptions import (
    ApplicationError,
    ConflictError,
    InvalidCredentialsError,
    NotFoundError,
    PermissionDeniedError,
)
from app.application.users.models import CreateUser, UpdateUser
from app.application.users.services import UserService
from app.core.config import Settings, get_settings
from app.ioc import create_container
from app.presentation.api.v1.router import router as v1_router

ALLOWED_ORIGIN = "https://woodandclay.ru"


async def _bootstrap_first_superuser(service: UserService, settings: Settings) -> None:
    if not settings.first_superuser_email or not settings.first_superuser_password:
        return

    email = str(settings.first_superuser_email)
    existing = await service.get_by_email(email)
    if existing is None:
        try:
            await service.create(
                CreateUser(
                    email=email,
                    username=settings.first_superuser_username,
                    password=settings.first_superuser_password,
                    role=settings.first_superuser_role,
                    name=settings.first_superuser_name,
                    surname=settings.first_superuser_surname,
                )
            )
            return
        except ConflictError:
            existing = await service.get_by_email(email)

    if existing is None or not existing.is_superuser:
        raise RuntimeError("FIRST_SUPERUSER identity conflicts with a regular user")

    await service.update(
        existing.id,
        UpdateUser(
            username=settings.first_superuser_username,
            role=settings.first_superuser_role,
            password=settings.first_superuser_password,
        ),
    )


def create_app() -> FastAPI:
    settings = get_settings()
    container = create_container()

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        if settings.first_superuser_email and settings.first_superuser_password:
            async with container() as request_container:
                service = await request_container.get(UserService)
                await _bootstrap_first_superuser(service, settings)
        yield
        await container.close()

    app = FastAPI(title="Market Backend", version="0.1.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[ALLOWED_ORIGIN],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(v1_router)
    app.mount(
        "/uploads",
        StaticFiles(directory=settings.upload_dir, check_dir=False),
        name="uploads",
    )
    setup_dishka(container, app)

    @app.exception_handler(ApplicationError)
    async def application_error(_: Request, error: ApplicationError) -> JSONResponse:
        status_code = 400
        if isinstance(error, InvalidCredentialsError):
            status_code = 401
        elif isinstance(error, PermissionDeniedError):
            status_code = 403
        elif isinstance(error, NotFoundError):
            status_code = 404
        elif isinstance(error, ConflictError):
            status_code = 409
        return JSONResponse(status_code=status_code, content={"detail": str(error)})

    @app.exception_handler(PaymentProviderError)
    async def payment_provider_error(_: Request, error: PaymentProviderError) -> JSONResponse:
        """The acquiring provider failed; 502 keeps it distinct from a client-side mistake."""
        return JSONResponse(status_code=502, content={"detail": str(error)})

    return app


app = create_app()
