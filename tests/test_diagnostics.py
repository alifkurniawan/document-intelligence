from fastapi.testclient import TestClient

from app.main import create_app


def test_public_errors_have_a_correlation_id_and_safe_envelope():
    with TestClient(create_app()) as client:
        response = client.post(
            "/documents",
            headers={"X-Correlation-ID": "request-42"},
            files={"file": ("file.pdf", b"not used", "application/pdf")},
        )

    assert response.status_code == 401
    assert response.headers["X-Correlation-ID"] == "request-42"
    assert response.json() == {
        "code": "authentication_required",
        "detail": "Bearer token is required",
        "correlation_id": "request-42",
    }


def test_invalid_correlation_ids_are_replaced():
    with TestClient(create_app()) as client:
        response = client.get("/health", headers={"X-Correlation-ID": "contains spaces"})

    assert response.status_code == 200
    assert response.headers["X-Correlation-ID"] != "contains spaces"
