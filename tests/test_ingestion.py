from __future__ import annotations

import io
from dataclasses import dataclass, field

from fastapi.testclient import TestClient
from PIL import Image

from app.config import Settings
from app.ingestion.auth import StaticTokenVerifier
from app.ingestion.registration import DocumentRegistrationService
from app.ingestion.storage import InMemoryArtifactStorage
from app.ingestion.validation import FileValidator
from app.main import create_app


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

    import asyncio

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
