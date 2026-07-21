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
