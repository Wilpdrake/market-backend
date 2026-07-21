from functools import lru_cache

from pydantic import Field
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


@lru_cache
def get_settings() -> Settings:
    return Settings()
