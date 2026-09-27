"""Async SQLAlchemy repository implementations."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.domain.models import (
    Artifact,
    ArtifactRole,
    Document,
    DocumentStatus,
    JobStatus,
    ProcessingJob,
)
from app.infrastructure.database.models import ArtifactModel, DocumentModel, ProcessingJobModel
from app.repositories.contracts import (
    ArtifactRepository,
    DocumentRepository,
    MetadataUnitOfWork,
    ProcessingJobRepository,
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


class SqlAlchemyDocumentRepository(DocumentRepository):
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


class SqlAlchemyArtifactRepository(ArtifactRepository):
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


class SqlAlchemyProcessingJobRepository(ProcessingJobRepository):
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


class SqlAlchemyMetadataUnitOfWork(MetadataUnitOfWork):
    """Async transaction boundary for metadata repositories."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self.session_factory = session_factory
        self.session: AsyncSession | None = None

    async def __aenter__(self) -> SqlAlchemyMetadataUnitOfWork:
        self.session = self.session_factory()
        self.documents = SqlAlchemyDocumentRepository(self.session)
        self.artifacts = SqlAlchemyArtifactRepository(self.session)
        self.jobs = SqlAlchemyProcessingJobRepository(self.session)
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
    "SqlAlchemyProcessingJobRepository",
]
