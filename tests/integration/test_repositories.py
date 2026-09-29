"""Docker Compose PostgreSQL integration coverage.

Run with INTEGRATION_DATABASE_URL set to a reachable PostgreSQL URL, for example:
INTEGRATION_DATABASE_URL=postgresql://app:app@localhost:5432/app uv run pytest tests/integration
"""

from __future__ import annotations

import asyncio
import os
from datetime import UTC, datetime

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import Settings
from app.core.database import create_engine
from app.models.entities import Artifact, Document
from app.repositories.document import SqlAlchemyMetadataUnitOfWork

DATABASE_URL = os.getenv("INTEGRATION_DATABASE_URL")
pytestmark = pytest.mark.skipif(
    not DATABASE_URL, reason="Docker Compose PostgreSQL is not configured"
)


def test_repository_round_trip_and_owner_isolation() -> None:
    asyncio.run(_run_repository_round_trip())


async def _run_repository_round_trip() -> None:
    settings = Settings(_env_file=None, database_url=DATABASE_URL)
    engine = create_engine(settings)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    document = Document.create(owner_id="account-1")
    artifact = Artifact.create_original(
        document_id=document.document_id,
        original_filename="contract.pdf",
        mime_type="application/pdf",
        size_bytes=10,
        sha256="b" * 64,
        storage_reference=f"documents/{document.document_id}/original",
        uploaded_at=datetime.now(UTC),
    )
    rolled_back_document = Document.create(owner_id="account-rollback")
    rolled_back_artifact = Artifact.create_original(
        document_id=rolled_back_document.document_id,
        original_filename="rollback.pdf",
        mime_type="application/pdf",
        size_bytes=4,
        sha256="c" * 64,
        storage_reference=f"documents/{rolled_back_document.document_id}/original",
        uploaded_at=datetime.now(UTC),
    )
    try:
        async with SqlAlchemyMetadataUnitOfWork(session_factory) as unit_of_work:
            await unit_of_work.documents.add(document)
            await unit_of_work.artifacts.add(artifact)
            await unit_of_work.commit()

        async with SqlAlchemyMetadataUnitOfWork(session_factory) as unit_of_work:
            assert await unit_of_work.documents.get(document.document_id, owner_id="other") is None
            loaded = await unit_of_work.documents.get(document.document_id, owner_id="account-1")
            assert loaded is not None
            assert loaded.original_artifact_id == artifact.artifact_id
            listed = await unit_of_work.documents.list(owner_id="account-1")
            assert [item.document_id for item in listed] == [document.document_id]
            assert await unit_of_work.documents.list(owner_id="other") == []

        with pytest.raises(RuntimeError, match="rollback sentinel"):
            async with SqlAlchemyMetadataUnitOfWork(session_factory) as unit_of_work:
                await unit_of_work.documents.add(rolled_back_document)
                await unit_of_work.artifacts.add(rolled_back_artifact)
                raise RuntimeError("rollback sentinel")

        async with SqlAlchemyMetadataUnitOfWork(session_factory) as unit_of_work:
            assert await unit_of_work.documents.get(rolled_back_document.document_id) is None
    finally:
        async with engine.begin() as connection:
            await connection.execute(
                text("DELETE FROM processing_jobs WHERE document_id = :document_id"),
                {"document_id": document.document_id},
            )
            await connection.execute(
                text("DELETE FROM artifacts WHERE document_id = :document_id"),
                {"document_id": document.document_id},
            )
            await connection.execute(
                text("DELETE FROM documents WHERE document_id = :document_id"),
                {"document_id": document.document_id},
            )
        await engine.dispose()
