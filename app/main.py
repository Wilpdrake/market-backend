from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from dishka.integrations.fastapi import setup_dishka
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.application.users.dto import CreateUser
from app.application.users.exceptions import (
    ApplicationError,
    ConflictError,
    InvalidCredentialsError,
    NotFoundError,
    PermissionDeniedError,
)
from app.application.users.services import UserService
from app.core.config import get_settings
from app.ioc import create_container
from app.presentation.api.v1.router import router as v1_router


def create_app() -> FastAPI:
    container = create_container()

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        settings = get_settings()
        if settings.first_superuser_email and settings.first_superuser_password:
            async with container() as request_container:
                service = await request_container.get(UserService)
                existing = await service.get_by_email(settings.first_superuser_email)
                if existing is None:
                    try:
                        await service.create(
                            CreateUser(
                                email=settings.first_superuser_email,
                                password=settings.first_superuser_password,
                                name=settings.first_superuser_name,
                                surname=settings.first_superuser_surname,
                                is_superuser=True,
                            )
                        )
                    except ConflictError:
                        existing = await service.get_by_email(settings.first_superuser_email)
                        if existing is None or not existing.is_superuser:
                            raise RuntimeError(
                                "FIRST_SUPERUSER_EMAIL belongs to a regular user"
                            ) from None
                elif not existing.is_superuser:
                    raise RuntimeError("FIRST_SUPERUSER_EMAIL belongs to a regular user")
        yield
        await container.close()

    app = FastAPI(title="Market Backend", version="0.1.0", lifespan=lifespan)
    app.include_router(v1_router)
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

    return app


app = create_app()
