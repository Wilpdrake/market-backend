from typing import cast
from unittest.mock import AsyncMock

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.users.exceptions import ConflictError
from app.domain.users.entities import User
from app.infrastructure.database.models import UserModel
from app.infrastructure.database.repositories import SqlAlchemyUserRepository


@pytest.mark.asyncio
async def test_save_maps_unique_conflict_and_rolls_back_session() -> None:
    session = AsyncMock(spec=AsyncSession)
    session.get.return_value = UserModel(
        email="existing@example.com",
        password_hash="hash",
    )
    session.commit.side_effect = IntegrityError("UPDATE users", {}, RuntimeError("unique"))
    repository = SqlAlchemyUserRepository(cast(AsyncSession, session))

    with pytest.raises(ConflictError):
        await repository.save(
            User(email="changed@example.com", username="changed", password_hash="hash")
        )

    session.rollback.assert_awaited_once_with()
    session.refresh.assert_not_awaited()
