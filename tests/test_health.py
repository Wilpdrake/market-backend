from fastapi.testclient import TestClient

from app.main import create_app


def test_liveness_reports_service_metadata() -> None:
    with TestClient(create_app()) as client:
        response = client.get("/api/v1/health/live")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "market-backend",
        "version": "0.1.0",
    }


def test_cors_allows_only_the_production_frontend_origin() -> None:
    with TestClient(create_app()) as client:
        allowed = client.options(
            "/api/v1/health/live",
            headers={
                "Origin": "https://woodandclay.ru",
                "Access-Control-Request-Method": "GET",
            },
        )
        rejected = client.options(
            "/api/v1/health/live",
            headers={
                "Origin": "https://example.com",
                "Access-Control-Request-Method": "GET",
            },
        )

    assert allowed.status_code == 200
    assert allowed.headers["access-control-allow-origin"] == "https://woodandclay.ru"
    assert rejected.status_code == 400
    assert "access-control-allow-origin" not in rejected.headers
