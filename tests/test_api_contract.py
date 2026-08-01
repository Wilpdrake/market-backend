from fastapi.testclient import TestClient

from app.main import create_app


def test_versioned_user_api_is_exposed_in_openapi() -> None:
    with TestClient(create_app()) as client:
        schema = client.get("/openapi.json").json()

    paths = schema["paths"]
    assert "/api/v1/auth/register" in paths
    assert "/api/v1/auth/token" in paths
    assert "/api/v1/users/me" in paths
    assert "/api/v1/users/{user_id}" in paths
    assert "/api/v1/verifications/email/request" in paths
    assert "/api/v1/verifications/email/confirm" in paths
    assert "/api/v1/verifications/phone/request" in paths
    assert "/api/v1/verifications/phone/confirm" in paths
    assert "/api/v1/verifications/telegram/request" in paths
    assert "/api/v1/telegram/webhook" in paths


def test_admin_api_is_exposed_in_openapi() -> None:
    with TestClient(create_app()) as client:
        schema = client.get("/openapi.json").json()
        paths = schema["paths"]

    assert "/api/v1/admin/auth/token" in paths
    assert "/api/v1/admin/auth/me" in paths
    assert "/api/v1/admin/users" in paths
    assert "/api/v1/admin/users/{user_id}" in paths
    assert "/api/v1/admin/products" in paths
    assert "/api/v1/admin/products/{product_id}" in paths

    models = schema["components"]["schemas"]
    user_input = models["AdminUserCreateRequest"]["properties"]
    user_output = models["AdminUserResponse"]["properties"]
    product_output = models["ProductResponse"]["properties"]

    assert {"password", "password_confirmation"} <= user_input.keys()
    assert "password" not in user_output
    assert {
        "uuid",
        "username",
        "name",
        "surname",
        "patronymic",
        "email",
        "contact_number",
        "telegram_username",
        "comment",
        "avatar_image",
        "header_image",
        "role",
        "is_superuser",
        "created_by",
        "created_at",
        "updated_at",
    } <= user_output.keys()
    assert {
        "uuid",
        "title",
        "description",
        "images",
        "header_image",
        "price",
        "ozon_price",
        "wb_price",
        "created_by",
        "updated_by",
        "created_at",
        "updated_at",
    } == product_output.keys()


def test_public_product_catalog_is_exposed_without_admin_prefix() -> None:
    """The storefront must not depend on an administrator-only endpoint."""
    with TestClient(create_app()) as client:
        schema = client.get("/openapi.json").json()
        paths = schema["paths"]

    assert "/api/v1/products" in paths
    assert "get" in paths["/api/v1/products"]
    assert "/api/v1/products/{product_id}" in paths
    public_output = schema["components"]["schemas"]["PublicProductResponse"]["properties"]
    assert "created_by" not in public_output
    assert "updated_by" not in public_output
