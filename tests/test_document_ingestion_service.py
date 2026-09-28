from __future__ import annotations

import asyncio
import io

import pytest
from PIL import Image

from app.core.config import Settings
from app.core.ingestion_errors import StorageError
from app.services.document_ingestion import DocumentIngestionService
from app.services.validation import FileValidator
from app.workers.contracts import ProcessingMessage


def png_bytes() -> bytes:
    output = io.BytesIO()
    Image.new("RGB", (2, 2), "white").save(output, format="PNG")
    return output.getvalue()


class FailingStorage:
    async def store(self, **kwargs):
        raise StorageError("storage unavailable")

    async def delete(self, storage_reference: str) -> None:
        raise AssertionError("delete is not needed when storage never succeeded")


class UnusedUnitOfWork:
    async def __aenter__(self):
        raise AssertionError("database should not be reached after storage failure")

    async def __aexit__(self, *args):
        return None


def test_service_accepts_injected_storage_and_cleans_up_on_failure() -> None:
    settings = Settings(_env_file=None)
    service = DocumentIngestionService(
        validator=FileValidator(settings),
        storage=FailingStorage(),
        unit_of_work_factory=UnusedUnitOfWork,
    )

    with pytest.raises(StorageError, match="storage unavailable"):
        asyncio.run(
            service.register(
                owner_id="owner-1",
                filename="scan.png",
                client_mime="image/png",
                source=png_bytes(),
            )
        )


def test_processing_message_contains_references_only() -> None:
    from uuid import uuid4

    message = ProcessingMessage(uuid4(), uuid4(), uuid4())
    payload = message.as_payload()

    assert set(payload) == {
        "document_id",
        "job_id",
        "original_artifact_id",
        "attempt",
        "correlation_id",
        "enqueued_at",
    }
    assert all(isinstance(value, (str, int)) for value in payload.values())
