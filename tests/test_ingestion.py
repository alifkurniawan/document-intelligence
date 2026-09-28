from __future__ import annotations

import asyncio
import io
from dataclasses import dataclass, field

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.api.app import create_app
from app.api.auth import StaticTokenVerifier
from app.core.config import Settings
from app.services.document_ingestion import DocumentRegistrationService
from app.services.validation import FileValidator
from app.storage.artifacts import InMemoryArtifactStorage


@dataclass
class MemoryRepository:
    values: list = field(default_factory=list)

    async def add(self, value):
        self.values.append(value)
        return value


class MemoryUnitOfWork:
    def __init__(self, state):
        self.documents = state[0]
        self.artifacts = state[1]
        self.jobs = state[2]

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return None

    async def commit(self):
        return None

    async def rollback(self):
        return None


def png_bytes() -> bytes:
    output = io.BytesIO()
    Image.new("RGB", (2, 2), "white").save(output, format="PNG")
    return output.getvalue()


def test_registration_stores_verifiable_original_and_queued_job() -> None:
    settings = Settings(_env_file=None)
    state = (MemoryRepository(), MemoryRepository(), MemoryRepository())
    storage = InMemoryArtifactStorage()
    service = DocumentRegistrationService(
        validator=FileValidator(settings),
        storage=storage,
        unit_of_work_factory=lambda: MemoryUnitOfWork(state),
    )

    result = asyncio.run(
        service.register(
            owner_id="owner-1",
            filename="scan.png",
            client_mime="image/png",
            source=png_bytes(),
        )
    )

    assert result.job.status == "queued"
    assert result.artifact.sha256
    assert asyncio.run(storage.read(result.artifact.storage_reference)) == png_bytes()
    assert len(state[0].values) == len(state[1].values) == len(state[2].values) == 1


def test_upload_route_maps_auth_and_returns_metadata() -> None:
    settings = Settings(_env_file=None)
    state = (MemoryRepository(), MemoryRepository(), MemoryRepository())
    app = create_app(settings)
    app.state.registration_service = DocumentRegistrationService(
        validator=FileValidator(settings),
        storage=InMemoryArtifactStorage(),
        unit_of_work_factory=lambda: MemoryUnitOfWork(state),
    )
    app.state.token_verifier = StaticTokenVerifier({"test-token": "owner-1"})

    with TestClient(app) as client:
        response = client.post(
            "/documents",
            headers={"Authorization": "Bearer test-token"},
            files={"file": ("scan.png", png_bytes(), "image/png")},
        )

    assert response.status_code == 200
    assert response.json()["uploader_id"] == "owner-1"
    assert response.json()["status"] == "queued"


def configured_app(*, settings: Settings | None = None):
    settings = settings or Settings(_env_file=None)
    application = create_app(settings)
    application.state.token_verifier = StaticTokenVerifier({"test-token": "owner-1"})
    return application


def test_upload_rejects_missing_authentication() -> None:
    with TestClient(configured_app()) as client:
        response = client.post("/documents", files={"file": ("scan.png", png_bytes(), "image/png")})

    assert response.status_code == 401
    assert response.json()["code"] == "authentication_required"
    assert response.headers["X-Correlation-ID"]


def test_upload_rejects_invalid_token() -> None:
    with TestClient(configured_app()) as client:
        response = client.post(
            "/documents",
            headers={"Authorization": "Bearer invalid-token"},
            files={"file": ("scan.png", png_bytes(), "image/png")},
        )

    assert response.status_code == 401
    assert response.json()["code"] == "authentication_failed"


@pytest.mark.parametrize(
    "filename, content, mime, expected_detail",
    [
        ("empty.png", b"", "image/png", "file is empty"),
        ("../unsafe.png", png_bytes(), "image/png", "filename is unsafe"),
        ("notes.txt", b"plain text", "text/plain", "file content is unreadable"),
    ],
)
def test_upload_rejects_invalid_file_requests(
    filename: str, content: bytes, mime: str, expected_detail: str
) -> None:
    application = configured_app()
    settings = application.state.settings
    application.state.registration_service = DocumentRegistrationService(
        validator=FileValidator(settings),
        storage=InMemoryArtifactStorage(),
        unit_of_work_factory=lambda: MemoryUnitOfWork(
            (MemoryRepository(), MemoryRepository(), MemoryRepository())
        ),
    )

    with TestClient(application) as client:
        response = client.post(
            "/documents",
            headers={"Authorization": "Bearer test-token"},
            files={"file": (filename, content, mime)},
        )

    assert response.status_code == 422
    assert response.json()["code"] == "invalid_file"
    assert expected_detail in response.json()["detail"]


def test_upload_rejects_oversized_file() -> None:
    settings = Settings(_env_file=None, max_upload_size_bytes=1)
    application = configured_app(settings=settings)
    application.state.registration_service = DocumentRegistrationService(
        validator=FileValidator(settings),
        storage=InMemoryArtifactStorage(),
        unit_of_work_factory=lambda: MemoryUnitOfWork(
            (MemoryRepository(), MemoryRepository(), MemoryRepository())
        ),
    )

    with TestClient(application) as client:
        response = client.post(
            "/documents",
            headers={"Authorization": "Bearer test-token"},
            files={"file": ("scan.png", png_bytes(), "image/png")},
        )

    assert response.status_code == 413
    assert response.json()["code"] == "file_too_large"


def test_document_routes_reject_malformed_document_id_with_not_found() -> None:
    with TestClient(configured_app()) as client:
        response = client.get(
            "/documents/not-a-uuid", headers={"Authorization": "Bearer test-token"}
        )

    assert response.status_code == 404
    assert response.json()["code"] == "not_found"


def test_upload_reports_unconfigured_database_dependency() -> None:
    with TestClient(configured_app()) as client:
        response = client.post(
            "/documents",
            headers={"Authorization": "Bearer test-token"},
            files={"file": ("scan.png", png_bytes(), "image/png")},
        )

    assert response.status_code == 503
    assert response.json()["code"] == "dependency_unavailable"
