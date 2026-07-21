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
