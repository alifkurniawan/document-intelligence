"""Owner-scoped document queries, original reads, and soft deletion."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from uuid import UUID

from app.core.ingestion_errors import NotFoundError
from app.models.entities import Artifact, Document, ProcessingJob
from app.storage.artifacts import ArtifactStorage


@dataclass(frozen=True, slots=True)
class DocumentRecord:
    document: Document
    artifact: Artifact
    job: ProcessingJob


@dataclass(frozen=True, slots=True)
class OriginalDocument:
    data: bytes
    filename: str
    mime_type: str


@dataclass(frozen=True, slots=True)
class DocumentPage:
    records: list[DocumentRecord]
    current_page: int
    total_data: int
    total_page: int


class DocumentManagementService:
    """Keep document repository and unit-of-work operations out of API routes."""

    def __init__(self, *, unit_of_work_factory: Callable, storage: ArtifactStorage) -> None:
        self.unit_of_work_factory = unit_of_work_factory
        self.storage = storage

    async def list_documents(
        self, *, owner_id: str, current_page: int, page_size: int
    ) -> DocumentPage:
        offset = (current_page - 1) * page_size
        async with self.unit_of_work_factory() as unit_of_work:
            total_data = await unit_of_work.documents.count(owner_id=owner_id)
            documents = await unit_of_work.documents.list(
                owner_id=owner_id,
                offset=offset,
                limit=page_size,
            )
            records = []
            for document in documents:
                if document.original_artifact_id is None:
                    continue
                artifact = await unit_of_work.artifacts.get(document.original_artifact_id)
                job = await unit_of_work.jobs.get_by_document(document.document_id)
                if artifact is not None and job is not None:
                    records.append(DocumentRecord(document, artifact, job))
            total_page = (total_data + page_size - 1) // page_size
            return DocumentPage(records, current_page, total_data, total_page)

    async def get_document(self, document_id: UUID, *, owner_id: str) -> DocumentRecord:
        async with self.unit_of_work_factory() as unit_of_work:
            document = await unit_of_work.documents.get(document_id, owner_id=owner_id)
            if document is None or document.original_artifact_id is None:
                raise NotFoundError("document was not found")
            artifact = await unit_of_work.artifacts.get(document.original_artifact_id)
            job = await unit_of_work.jobs.get_by_document(document_id)
            if artifact is None or job is None:
                raise NotFoundError("document metadata was not found")
            return DocumentRecord(document, artifact, job)

    async def delete_document(self, document_id: UUID, *, owner_id: str) -> Document:
        async with self.unit_of_work_factory() as unit_of_work:
            document = await unit_of_work.documents.mark_deleted(document_id, owner_id=owner_id)
            if document is None:
                raise NotFoundError("document was not found")
            await unit_of_work.commit()
            return document

    async def get_original(self, document_id: UUID, *, owner_id: str) -> OriginalDocument:
        record = await self.get_document(document_id, owner_id=owner_id)
        data = await self.storage.read(record.artifact.storage_reference)
        return OriginalDocument(
            data=data,
            filename=record.artifact.original_filename,
            mime_type=record.artifact.mime_type,
        )


__all__ = ["DocumentManagementService", "DocumentPage", "DocumentRecord", "OriginalDocument"]
