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
