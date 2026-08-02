from typing import cast
from unittest.mock import AsyncMock

import pytest

from app.application.users.services import UserService
from app.core.config import Settings
from app.domain.users.models import User
from app.main import _bootstrap_first_superuser


@pytest.mark.asyncio
async def test_bootstrap_reconciles_existing_developer_identity_and_password() -> None:
    existing = User(
        email="owner@example.com",
        username=None,
        role="admin",
        password_hash="hash",
        is_superuser=True,
    )
    service = AsyncMock(spec=UserService)
    service.get_by_email.return_value = existing
    settings = Settings(
        first_superuser_email="owner@example.com",
        first_superuser_password="existing-secret",
    )

    await _bootstrap_first_superuser(cast(UserService, service), settings)

    update = service.update.await_args
    assert update.args[0] == existing.id
    assert update.args[1].username == "wilpdrake"
    assert update.args[1].role == "developer"
    assert update.args[1].password == "existing-secret"
