from functools import lru_cache
from pathlib import Path
from typing import Literal
from urllib.parse import quote

from pydantic import EmailStr, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.domain.users.models import normalize_username


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Market Backend"
    app_version: str = "0.1.0"
    environment: str = "development"
    debug: bool = False
    upload_dir: Path = Path("uploads")
    # DATABASE_URL may override these components. Component settings are safer for Compose
    # because URL-sensitive characters in credentials are encoded here, not in shell/YAML.
    database_url: str | None = None
    postgres_user: str = "market"
    postgres_password: str = "changeme"
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "market"
    secret_key: str = Field(default="change-me-in-production", min_length=16)
    access_token_expire_minutes: int = 30
    telegram_bot_token: str | None = None
    telegram_bot_username: str = "market_bot"
    telegram_webhook_secret: str | None = None
    first_superuser_email: EmailStr | None = None
    first_superuser_username: str | None = "wilpdrake"
    first_superuser_role: Literal["moder", "admin", "owner", "developer"] = "developer"
    first_superuser_password: str | None = Field(default=None, min_length=8)
    first_superuser_name: str = "Admin"
    first_superuser_surname: str = "Administrator"

    @property
    def resolved_database_url(self) -> str:
        if self.database_url:
            return self.database_url
        user = quote(self.postgres_user, safe="")
        password = quote(self.postgres_password, safe="")
        database = quote(self.postgres_db, safe="")
        return (
            f"postgresql+asyncpg://{user}:{password}@{self.postgres_host}:"
            f"{self.postgres_port}/{database}"
        )

    @field_validator(
        "database_url",
        "first_superuser_email",
        "first_superuser_username",
        "first_superuser_password",
        mode="before",
    )
    @classmethod
    def empty_optional_value_is_none(cls, value: object) -> object:
        return None if value == "" else value

    @field_validator("first_superuser_username")
    @classmethod
    def normalize_initial_admin_username(cls, value: str | None) -> str | None:
        return normalize_username(value) if value is not None else None

    @model_validator(mode="after")
    def initial_admin_credentials_are_a_pair(self) -> "Settings":
        if bool(self.first_superuser_email) != bool(self.first_superuser_password):
            raise ValueError(
                "FIRST_SUPERUSER_EMAIL and FIRST_SUPERUSER_PASSWORD must be configured together"
            )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
