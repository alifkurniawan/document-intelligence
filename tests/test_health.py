from fastapi.testclient import TestClient

from app.main import app


def test_application_starts() -> None:
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200


def test_health_response_is_minimal_and_unauthenticated() -> None:
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
