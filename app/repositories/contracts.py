"""Async repository contracts expressed in domain terms."""

from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from app.domain.models import Artifact, Document, ProcessingJob


class DocumentRepository(ABC):
    @abstractmethod
    async def add(self, document: Document) -> Document: ...

    @abstractmethod
    async def get(self, document_id: UUID, *, owner_id: str | None = None) -> Document | None: ...


class ArtifactRepository(ABC):
    @abstractmethod
    async def add(self, artifact: Artifact) -> Artifact: ...

    @abstractmethod
    async def get(self, artifact_id: UUID) -> Artifact | None: ...

    @abstractmethod
    async def get_original(self, document_id: UUID) -> Artifact | None: ...


class ProcessingJobRepository(ABC):
    @abstractmethod
    async def add(self, job: ProcessingJob) -> ProcessingJob: ...

    @abstractmethod
    async def get(self, job_id: UUID) -> ProcessingJob | None: ...


class MetadataUnitOfWork(ABC):
    """Transaction boundary for document and artifact metadata."""

    documents: DocumentRepository
    artifacts: ArtifactRepository
    jobs: ProcessingJobRepository

    @abstractmethod
    async def __aenter__(self) -> MetadataUnitOfWork: ...

    @abstractmethod
    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: object | None,
    ) -> None: ...

    @abstractmethod
    async def commit(self) -> None: ...

    @abstractmethod
    async def rollback(self) -> None: ...


__all__ = [
    "ArtifactRepository",
    "DocumentRepository",
    "MetadataUnitOfWork",
    "ProcessingJobRepository",
]
