from uuid import UUID

import pytest
from pydantic import BaseModel, ValidationError

from app.application.products.models import CreateProduct
from app.application.users.models import CreateUser
from app.domain.products.models import Product
from app.domain.users.models import User
from app.presentation.api.v1.schemas import RegisterRequest


def test_domain_and_application_data_are_pydantic_models() -> None:
    actor_id = UUID("00000000-0000-0000-0000-000000000001")

    user = User(email="user@example.com", password_hash="hash")
    product = Product(title="Plate", created_by=actor_id, updated_by=actor_id)

    assert isinstance(user, BaseModel)
    assert isinstance(product, BaseModel)
    assert issubclass(CreateUser, BaseModel)
    assert issubclass(CreateProduct, BaseModel)
    assert user.model_dump()["email"] == "user@example.com"


def test_application_commands_are_immutable_and_reject_unknown_fields() -> None:
    command = CreateUser(email="user@example.com", password="strong-password")

    with pytest.raises(ValidationError):
        command.email = "other@example.com"

    with pytest.raises(ValidationError):
        CreateUser(
            email="user@example.com",
            password="strong-password",
            unexpected="value",
        )


def test_domain_models_support_validated_assignment_and_copy_on_update() -> None:
    user = User(email="user@example.com", password_hash="hash")

    updated = user.model_copy(update={"is_active": False})

    assert updated.is_active is False
    assert user.is_active is True
    with pytest.raises(ValidationError):
        user.is_active = "not-a-boolean"


def test_http_models_reject_unknown_json_fields() -> None:
    with pytest.raises(ValidationError):
        RegisterRequest(
            email="user@example.com",
            password="strong-password",
            unexpected="value",
        )
