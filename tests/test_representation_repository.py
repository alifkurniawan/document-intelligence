from __future__ import annotations

import asyncio
from uuid import uuid4

from app.models.database import DocumentRepresentationModel
from app.models.understanding import (
    BlockType,
    ContentBlock,
    DocumentRepresentation,
    PageRepresentation,
    ProcessingProvenance,
)
from app.repositories.document import SqlAlchemyRepresentationRepository


class SessionDouble:
    def __init__(self) -> None:
        self.value = None

    def add(self, value) -> None:
        self.value = value

    async def flush(self) -> None:
        return None

    async def get(self, model, key):
        return self.value if self.value and self.value.representation_id == key else None


def representation() -> DocumentRepresentation:
    document_id = uuid4()
    artifact_id = uuid4()
    block = ContentBlock(
        type=BlockType.TEXT,
        text="2026-01-01 ID ABC-123",
        page_number=1,
        reading_order=0,
        bbox=(1, 2, 3, 4),
    )
    return DocumentRepresentation(
        representation_id=uuid4(),
        document_id=document_id,
        artifact_id=artifact_id,
        mime_type="application/pdf",
        pages=(PageRepresentation(1, 100, 200, (block,)),),
        blocks=(block,),
        tables=(),
        images=(),
        provenance=ProcessingProvenance(
            processor="test",
            processor_version="1",
            logic_version="1",
            artifact_id=artifact_id,
            storage_reference="documents/a/original.pdf",
        ),
    )


def test_representation_repository_round_trips_derived_content_without_binary_data() -> None:
    session = SessionDouble()
    repository = SqlAlchemyRepresentationRepository(session)
    expected = representation()

    asyncio.run(repository.add(expected))

    assert isinstance(session.value, DocumentRepresentationModel)
    assert "2026-01-01 ID ABC-123" in session.value.payload
    assert "original.pdf" not in session.value.payload
    actual = asyncio.run(repository.get(expected.representation_id))

    assert actual is not None
    assert actual.document_id == expected.document_id
    assert actual.artifact_id == expected.artifact_id
    assert actual.blocks[0].bbox == (1, 2, 3, 4)
