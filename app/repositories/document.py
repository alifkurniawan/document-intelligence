"""Async SQLAlchemy repository implementations."""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.database import (
    ArtifactModel,
    DocumentModel,
    DocumentRepresentationModel,
    OutboxMessageModel,
    ProcessingJobModel,
)
from app.models.entities import (
    Artifact,
    ArtifactRole,
    Document,
    DocumentStatus,
    JobStatus,
    OutboxMessage,
    ProcessingJob,
)
from app.models.understanding import (
    BlockType,
    ContentBlock,
    DocumentRepresentation,
    PageRepresentation,
    ProcessingProvenance,
    ProcessingStatus,
)
from app.repositories.errors import RepositoryConflict


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


def _document_entity(model: DocumentModel, original_artifact_id: UUID | None) -> Document:
    return Document(
        document_id=model.document_id,
        owner_id=model.owner_id,
        status=DocumentStatus(model.status),
        created_at=_aware(model.created_at),
        updated_at=_aware(model.updated_at),
        original_artifact_id=original_artifact_id,
        deleted_at=_aware(model.deleted_at) if model.deleted_at is not None else None,
        deleted_by=model.deleted_by,
    )


def _artifact_entity(model: ArtifactModel) -> Artifact:
    return Artifact(
        artifact_id=model.artifact_id,
        document_id=model.document_id,
        role=ArtifactRole(model.role),
        original_filename=model.original_filename,
        mime_type=model.mime_type,
        size_bytes=model.size_bytes,
        sha256=model.sha256,
        storage_reference=model.storage_reference,
        uploaded_at=_aware(model.uploaded_at),
    )


def _job_entity(model: ProcessingJobModel) -> ProcessingJob:
    return ProcessingJob(
        job_id=model.job_id,
        document_id=model.document_id,
        original_artifact_id=model.original_artifact_id,
        status=JobStatus(model.status),
        retry_count=model.retry_count,
        last_error=model.last_error,
        created_at=_aware(model.created_at),
        updated_at=_aware(model.updated_at),
    )


class SqlAlchemyDocumentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, document: Document) -> Document:
        self.session.add(
            DocumentModel(
                document_id=document.document_id,
                owner_id=document.owner_id,
                status=document.status.value,
                created_at=document.created_at,
                updated_at=document.updated_at,
            )
        )
        try:
            await self.session.flush()
        except IntegrityError as exc:
            raise RepositoryConflict("document already exists or violates a constraint") from exc
        return document

    async def get(self, document_id: UUID, *, owner_id: str | None = None) -> Document | None:
        statement = select(DocumentModel).where(DocumentModel.document_id == document_id)
        if owner_id is not None:
            statement = statement.where(DocumentModel.owner_id == owner_id)
        model = await self.session.scalar(statement)
        if model is None:
            return None
        original_artifact_id = await self.session.scalar(
            select(ArtifactModel.artifact_id).where(
                ArtifactModel.document_id == document_id,
                ArtifactModel.role == ArtifactRole.ORIGINAL.value,
            )
        )
        return _document_entity(model, original_artifact_id)

    async def list(self, *, owner_id: str, offset: int = 0, limit: int = 20) -> list[Document]:
        """Return documents visible to one owner, newest first."""
        models = (
            await self.session.scalars(
                select(DocumentModel)
                .where(DocumentModel.owner_id == owner_id, DocumentModel.deleted_at.is_(None))
                .order_by(DocumentModel.created_at.desc(), DocumentModel.document_id.desc())
                .offset(offset)
                .limit(limit)
            )
        ).all()
        documents = []
        for model in models:
            original_artifact_id = await self.session.scalar(
                select(ArtifactModel.artifact_id).where(
                    ArtifactModel.document_id == model.document_id,
                    ArtifactModel.role == ArtifactRole.ORIGINAL.value,
                )
            )
            documents.append(_document_entity(model, original_artifact_id))
        return documents

    async def count(self, *, owner_id: str) -> int:
        """Count visible documents for one owner."""
        total = await self.session.scalar(
            select(func.count())
            .select_from(DocumentModel)
            .where(DocumentModel.owner_id == owner_id, DocumentModel.deleted_at.is_(None))
        )
        return int(total or 0)

    async def mark_deleted(self, document_id: UUID, *, owner_id: str) -> Document | None:
        """Soft-delete an owner's document, retaining who and when for audit."""
        model = await self.session.scalar(
            select(DocumentModel)
            .where(DocumentModel.document_id == document_id, DocumentModel.owner_id == owner_id)
            .with_for_update()
        )
        if model is None:
            return None
        if model.deleted_at is None:
            document = _document_entity(model, None).mark_deleted(deleted_by=owner_id)
            model.deleted_at = document.deleted_at
            model.deleted_by = document.deleted_by
            model.updated_at = document.updated_at
            await self.session.flush()
        original_artifact_id = await self.session.scalar(
            select(ArtifactModel.artifact_id).where(
                ArtifactModel.document_id == document_id,
                ArtifactModel.role == ArtifactRole.ORIGINAL.value,
            )
        )
        return _document_entity(model, original_artifact_id)


class SqlAlchemyArtifactRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, artifact: Artifact) -> Artifact:
        self.session.add(
            ArtifactModel(
                artifact_id=artifact.artifact_id,
                document_id=artifact.document_id,
                role=artifact.role.value,
                original_filename=artifact.original_filename,
                mime_type=artifact.mime_type,
                size_bytes=artifact.size_bytes,
                sha256=artifact.sha256,
                storage_reference=artifact.storage_reference,
                uploaded_at=artifact.uploaded_at,
            )
        )
        try:
            await self.session.flush()
        except IntegrityError as exc:
            raise RepositoryConflict("artifact already exists or violates a constraint") from exc
        return artifact

    async def get(self, artifact_id: UUID) -> Artifact | None:
        model = await self.session.get(ArtifactModel, artifact_id)
        return _artifact_entity(model) if model is not None else None

    async def get_original(self, document_id: UUID) -> Artifact | None:
        model = await self.session.scalar(
            select(ArtifactModel).where(
                ArtifactModel.document_id == document_id,
                ArtifactModel.role == ArtifactRole.ORIGINAL.value,
            )
        )
        return _artifact_entity(model) if model is not None else None


class SqlAlchemyProcessingJobRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, job: ProcessingJob) -> ProcessingJob:
        self.session.add(
            ProcessingJobModel(
                job_id=job.job_id,
                document_id=job.document_id,
                original_artifact_id=job.original_artifact_id,
                status=job.status.value,
                retry_count=job.retry_count,
                last_error=job.last_error,
                created_at=job.created_at,
                updated_at=job.updated_at,
            )
        )
        try:
            await self.session.flush()
        except IntegrityError as exc:
            raise RepositoryConflict("job already exists or violates a constraint") from exc
        return job

    async def get(self, job_id: UUID) -> ProcessingJob | None:
        model = await self.session.get(ProcessingJobModel, job_id)
        return _job_entity(model) if model is not None else None

    async def get_by_document(self, document_id: UUID) -> ProcessingJob | None:
        model = await self.session.scalar(
            select(ProcessingJobModel)
            .where(ProcessingJobModel.document_id == document_id)
            .order_by(ProcessingJobModel.created_at.desc())
        )
        return _job_entity(model) if model is not None else None

    async def update(self, job: ProcessingJob) -> ProcessingJob:
        model = await self.session.get(ProcessingJobModel, job.job_id)
        if model is None:
            raise RepositoryConflict("job does not exist")
        model.status = job.status.value
        model.retry_count = job.retry_count
        model.last_error = job.last_error
        model.updated_at = job.updated_at
        await self.session.flush()
        return job


def _outbox_entity(model: OutboxMessageModel) -> OutboxMessage:
    return OutboxMessage(
        outbox_id=model.outbox_id,
        job_id=model.job_id,
        document_id=model.document_id,
        original_artifact_id=model.original_artifact_id,
        routing_key=model.routing_key,
        attempts=model.attempts,
        published_at=_aware(model.published_at) if model.published_at else None,
        created_at=_aware(model.created_at),
    )


class SqlAlchemyOutboxRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, message: OutboxMessage) -> OutboxMessage:
        self.session.add(
            OutboxMessageModel(
                outbox_id=message.outbox_id,
                job_id=message.job_id,
                document_id=message.document_id,
                original_artifact_id=message.original_artifact_id,
                routing_key=message.routing_key,
                attempts=message.attempts,
                published_at=message.published_at,
                created_at=message.created_at,
            )
        )
        await self.session.flush()
        return message

    async def pending(self, *, limit: int = 100) -> list[OutboxMessage]:
        rows = (
            await self.session.scalars(
                select(OutboxMessageModel)
                .where(OutboxMessageModel.published_at.is_(None))
                .order_by(OutboxMessageModel.created_at)
                .limit(limit)
            )
        ).all()
        return [_outbox_entity(row) for row in rows]

    async def mark_published(self, outbox_id: UUID) -> None:
        model = await self.session.get(OutboxMessageModel, outbox_id)
        if model is not None:
            model.published_at = datetime.now(UTC)
            await self.session.flush()

    async def mark_attempted(self, outbox_id: UUID) -> None:
        model = await self.session.get(OutboxMessageModel, outbox_id)
        if model is not None:
            model.attempts += 1
            await self.session.flush()


def _representation_payload(representation: DocumentRepresentation) -> str:
    def block(value: ContentBlock) -> dict:
        result = asdict(value)
        result["block_id"] = str(value.block_id)
        result["type"] = value.type.value
        return result

    return json.dumps(
        {
            "pages": [
                {
                    "number": page.number,
                    "width": page.width,
                    "height": page.height,
                    "blocks": [block(item) for item in page.blocks],
                }
                for page in representation.pages
            ],
            "blocks": [block(item) for item in representation.blocks],
            "tables": [block(item) for item in representation.tables],
            "images": [block(item) for item in representation.images],
        },
        separators=(",", ":"),
    )


class SqlAlchemyRepresentationRepository:
    """Persistence boundary for derived representations, never original bytes."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, representation: DocumentRepresentation) -> DocumentRepresentation:
        now = datetime.now(UTC)
        self.session.add(
            DocumentRepresentationModel(
                representation_id=representation.representation_id,
                document_id=representation.document_id,
                artifact_id=representation.artifact_id,
                status=ProcessingStatus.COMPLETED.value,
                mime_type=representation.mime_type,
                processor=representation.provenance.processor,
                processor_version=representation.provenance.processor_version,
                logic_version=representation.provenance.logic_version,
                storage_reference=representation.provenance.storage_reference,
                payload=_representation_payload(representation),
                created_at=representation.created_at,
                updated_at=now,
            )
        )
        await self.session.flush()
        return representation

    async def get(self, representation_id: UUID) -> DocumentRepresentation | None:
        model = await self.session.get(DocumentRepresentationModel, representation_id)
        if model is None or model.status != ProcessingStatus.COMPLETED.value:
            return None
        payload = json.loads(model.payload)

        def block(value: dict) -> ContentBlock:
            return ContentBlock(
                block_id=UUID(value["block_id"]),
                type=BlockType(value["type"]),
                text=value["text"],
                page_number=value.get("page_number"),
                reading_order=value.get("reading_order"),
                bbox=tuple(value["bbox"]) if value.get("bbox") else None,
                source_reference=value.get("source_reference"),
            )

        blocks = tuple(block(item) for item in payload["blocks"])
        pages = tuple(
            PageRepresentation(
                page["number"],
                page.get("width"),
                page.get("height"),
                tuple(block(item) for item in page["blocks"]),
            )
            for page in payload["pages"]
        )
        return DocumentRepresentation(
            representation_id=model.representation_id,
            document_id=model.document_id,
            artifact_id=model.artifact_id,
            mime_type=model.mime_type,
            pages=pages,
            blocks=blocks,
            tables=tuple(block(item) for item in payload["tables"]),
            images=tuple(block(item) for item in payload["images"]),
            provenance=ProcessingProvenance(
                processor=model.processor,
                processor_version=model.processor_version,
                logic_version=model.logic_version,
                artifact_id=model.artifact_id,
                storage_reference=model.storage_reference,
                processed_at=_aware(model.created_at),
            ),
            created_at=_aware(model.created_at),
        )

    async def latest(self, document_id: UUID) -> DocumentRepresentation | None:
        model = await self.session.scalar(
            select(DocumentRepresentationModel)
            .where(
                DocumentRepresentationModel.document_id == document_id,
                DocumentRepresentationModel.status == ProcessingStatus.COMPLETED.value,
            )
            .order_by(DocumentRepresentationModel.created_at.desc())
        )
        return await self.get(model.representation_id) if model else None


class SqlAlchemyMetadataUnitOfWork:
    """Async transaction boundary for metadata repositories."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self.session_factory = session_factory
        self.session: AsyncSession | None = None

    async def __aenter__(self) -> SqlAlchemyMetadataUnitOfWork:
        self.session = self.session_factory()
        self.documents = SqlAlchemyDocumentRepository(self.session)
        self.artifacts = SqlAlchemyArtifactRepository(self.session)
        self.jobs = SqlAlchemyProcessingJobRepository(self.session)
        self.outbox = SqlAlchemyOutboxRepository(self.session)
        self.representations = SqlAlchemyRepresentationRepository(self.session)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: object | None,
    ) -> None:
        if self.session is None:
            return
        if exc_type is not None:
            await self.session.rollback()
        await self.session.close()

    async def commit(self) -> None:
        if self.session is None:
            raise RuntimeError("unit of work must be entered before commit")
        await self.session.commit()

    async def rollback(self) -> None:
        if self.session is None:
            raise RuntimeError("unit of work must be entered before rollback")
        await self.session.rollback()


__all__ = [
    "SqlAlchemyArtifactRepository",
    "SqlAlchemyDocumentRepository",
    "SqlAlchemyMetadataUnitOfWork",
    "SqlAlchemyOutboxRepository",
    "SqlAlchemyProcessingJobRepository",
    "SqlAlchemyRepresentationRepository",
]
