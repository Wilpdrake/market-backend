import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.infrastructure.payments.tbank import StubPaymentGateway
from app.ioc import AppProvider


def test_blank_initial_admin_credentials_are_optional() -> None:
    settings = Settings(first_superuser_email="", first_superuser_password="")

    assert settings.first_superuser_email is None
    assert settings.first_superuser_password is None


def test_initial_developer_defaults_to_wilpdrake_and_highest_role() -> None:
    settings = Settings()

    assert settings.first_superuser_username == "wilpdrake"
    assert settings.first_superuser_role == "developer"


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


def test_development_without_tbank_credentials_uses_stub_gateway() -> None:
    gateway = AppProvider().payment_gateway(Settings(environment="development"))

    assert isinstance(gateway, StubPaymentGateway)


def test_production_without_tbank_credentials_refuses_to_start_payments() -> None:
    with pytest.raises(RuntimeError, match="TBANK_TERMINAL_KEY"):
        AppProvider().payment_gateway(Settings(environment="production"))


def test_production_tbank_requires_public_https_notification_url() -> None:
    settings = Settings(
        environment="production",
        tbank_terminal_key="terminal",
        tbank_password="password",
        tbank_notification_url="http://backend:8000/api/v1/payments/tbank/webhook",
    )

    with pytest.raises(RuntimeError, match="public HTTPS"):
        AppProvider().payment_gateway(settings)
