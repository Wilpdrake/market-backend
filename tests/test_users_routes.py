import ast
from pathlib import Path

from app.presentation.api.v1 import users as users_routes


def test_generic_admin_update_forwards_actor_to_service() -> None:
    tree = ast.parse(Path(users_routes.__file__).read_text())
    handler = next(
        node
        for node in tree.body
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "update_user"
    )
    update_calls = [
        node
        for node in ast.walk(handler)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "update"
    ]

    assert len(update_calls) == 1
    assert any(keyword.arg == "actor" for keyword in update_calls[0].keywords)
