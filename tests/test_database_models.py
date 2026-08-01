from typing import cast

from sqlalchemy import CheckConstraint, Table

from app.infrastructure.database.models import UserModel


def test_user_role_constraint_is_present_in_orm_metadata() -> None:
    table = cast(Table, UserModel.__table__)
    constraints = {
        constraint.name
        for constraint in table.constraints
        if isinstance(constraint, CheckConstraint)
    }

    assert "ck_users_role" in constraints
    assert "ck_users_username_format" in constraints
    assert table.c.role.server_default is not None
