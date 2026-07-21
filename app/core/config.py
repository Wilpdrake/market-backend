from functools import lru_cache

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Market Backend"
    app_version: str = "0.1.0"
    environment: str = "development"
    debug: bool = False
    database_url: str = "postgresql+asyncpg://market:changeme@localhost:5432/market"
    secret_key: str = Field(default="change-me-in-production", min_length=16)
    access_token_expire_minutes: int = 30
    telegram_bot_token: str | None = None
    telegram_bot_username: str = "market_bot"
    telegram_webhook_secret: str | None = None
    first_superuser_email: str | None = None
    first_superuser_password: str | None = Field(default=None, min_length=8)
    first_superuser_name: str = "Admin"
    first_superuser_surname: str = "Administrator"

    @field_validator("first_superuser_email", "first_superuser_password", mode="before")
    @classmethod
    def empty_initial_admin_value_is_none(cls, value: object) -> object:
        return None if value == "" else value

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
