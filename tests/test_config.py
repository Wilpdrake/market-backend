import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_blank_initial_admin_credentials_are_optional() -> None:
    settings = Settings(first_superuser_email="", first_superuser_password="")

    assert settings.first_superuser_email is None
    assert settings.first_superuser_password is None


def test_initial_admin_credentials_must_be_configured_together() -> None:
    with pytest.raises(ValidationError):
        Settings(
            first_superuser_email="admin@example.com",
            first_superuser_password="",
        )


def test_initial_admin_email_must_be_deliverable() -> None:
    with pytest.raises(ValidationError):
        Settings(
            first_superuser_email="admin@example.test",
            first_superuser_password="valid-password",
        )


def test_database_url_is_built_with_url_encoded_credentials() -> None:
    settings = Settings(
        database_url=None,
        postgres_user="market@example",
        postgres_password="p@ss:/word",
        postgres_host="postgres",
        postgres_db="market",
    )

    assert settings.resolved_database_url == (
        "postgresql+asyncpg://market%40example:p%40ss%3A%2Fword@postgres:5432/market"
    )


def test_database_url_preserves_spaces_in_credentials() -> None:
    settings = Settings(
        database_url=None,
        postgres_user="market user",
        postgres_password="space password",
        postgres_host="postgres",
        postgres_db="market db",
    )
    assert settings.resolved_database_url == (
        "postgresql+asyncpg://market%20user:space%20password@postgres:5432/market%20db"
    )


def test_initial_admin_username_is_normalized_and_validated() -> None:
    settings = Settings(
        first_superuser_email="admin@example.com",
        first_superuser_password="valid-password",
        first_superuser_username=" Owner.Login ",
    )
    assert settings.first_superuser_username == "owner.login"

    with pytest.raises(ValidationError):
        Settings(
            first_superuser_email="admin@example.com",
            first_superuser_password="valid-password",
            first_superuser_username="   ",
        )
