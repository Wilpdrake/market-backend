from copy import deepcopy
from pathlib import Path
from typing import Any

import yaml
from fastapi.openapi.models import OpenAPI

from app.main import create_app

OPENAPI_PATH = Path(__file__).parents[1] / "openapi" / "openapi.yaml"
HTTP_METHODS = {"get", "put", "post", "delete", "options", "head", "patch", "trace"}
PLANNED_OPERATIONS = {
    ("/api/v1/auth/google", "post"),
    ("/api/v1/payments/tbank/options", "get"),
    ("/api/v1/orders", "post"),
    ("/api/v1/orders/{order_id}", "get"),
    ("/api/v1/orders/{order_id}/payments/tbank", "post"),
    ("/api/v1/orders/{order_id}/payment", "get"),
    ("/api/v1/orders/{order_id}/payment/cancel", "post"),
    ("/api/v1/payments/tbank/webhook", "post"),
}


def _load_contract() -> dict[str, Any]:
    document = yaml.safe_load(OPENAPI_PATH.read_text(encoding="utf-8"))
    assert isinstance(document, dict)
    return document


def _operations(document: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
    return {
        (path, method): operation
        for path, path_item in document["paths"].items()
        for method, operation in path_item.items()
        if method in HTTP_METHODS
    }


def test_static_openapi_is_valid_and_has_resolvable_local_references() -> None:
    document = _load_contract()

    OpenAPI.model_validate(document)

    def visit(value: Any) -> None:
        if isinstance(value, dict):
            reference = value.get("$ref")
            if isinstance(reference, str) and reference.startswith("#/"):
                target: Any = document
                for part in reference[2:].split("/"):
                    target = target[part.replace("~1", "/").replace("~0", "~")]
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    visit(document)


def test_static_openapi_contains_current_and_planned_operations() -> None:
    document = _load_contract()
    operations = _operations(document)
    runtime_document = create_app().openapi()
    runtime_operations = _operations(runtime_document)

    implemented = {
        key for key, operation in operations.items() if operation.get("x-status") == "implemented"
    }
    planned = {
        key for key, operation in operations.items() if operation.get("x-status") == "planned"
    }

    assert implemented == runtime_operations.keys()
    assert planned == PLANNED_OPERATIONS
    assert len(operations) == len(implemented) + len(planned)

    for key, runtime_operation in runtime_operations.items():
        static_operation = deepcopy(operations[key])
        assert static_operation.pop("x-status") == "implemented"
        assert static_operation == runtime_operation

    for section, runtime_components in runtime_document.get("components", {}).items():
        static_components = document["components"][section]
        for name, runtime_component in runtime_components.items():
            assert static_components[name] == runtime_component


def test_static_openapi_operation_ids_are_unique() -> None:
    operation_ids = [
        operation["operationId"] for operation in _operations(_load_contract()).values()
    ]

    assert len(operation_ids) == len(set(operation_ids))
