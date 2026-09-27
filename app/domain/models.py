"""Immutable, provider-neutral ingestion entities and lifecycle rules."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from app.domain.errors import DomainError, InvalidStateTransition, OriginalArtifactError


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _require_text(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise DomainError(f"{field_name} must be a non-empty string")
    return value


class ArtifactRole(StrEnum):
    ORIGINAL = "original"
    DERIVATIVE = "derivative"


class DocumentStatus(StrEnum):
    RECEIVED = "received"
    VALIDATING = "validating"
    REGISTERED = "registered"
    STORED = "stored"
    QUEUED = "queued"


class JobStatus(StrEnum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


DOCUMENT_TRANSITIONS: dict[DocumentStatus, set[DocumentStatus]] = {
    DocumentStatus.RECEIVED: {DocumentStatus.VALIDATING},
    DocumentStatus.VALIDATING: {DocumentStatus.REGISTERED},
    DocumentStatus.REGISTERED: {DocumentStatus.STORED},
    DocumentStatus.STORED: {DocumentStatus.QUEUED},
    DocumentStatus.QUEUED: set(),
}

JOB_TRANSITIONS: dict[JobStatus, set[JobStatus]] = {
    JobStatus.QUEUED: {JobStatus.PROCESSING},
    JobStatus.PROCESSING: {JobStatus.COMPLETED, JobStatus.FAILED},
    JobStatus.COMPLETED: set(),
    JobStatus.FAILED: {JobStatus.QUEUED},
}


@dataclass(frozen=True, slots=True)
class Artifact:
    artifact_id: UUID
    document_id: UUID
    role: ArtifactRole
    original_filename: str
    mime_type: str
    size_bytes: int
    sha256: str
    storage_reference: str
    uploaded_at: datetime

    def __post_init__(self) -> None:
        _require_text(self.original_filename, "original_filename")
        _require_text(self.mime_type, "mime_type")
        _require_text(self.sha256, "sha256")
        _require_text(self.storage_reference, "storage_reference")
        if self.size_bytes < 0:
            raise DomainError("size_bytes cannot be negative")
        if self.uploaded_at.tzinfo is None:
            raise DomainError("uploaded_at must be timezone-aware")

    @classmethod
    def create_original(
        cls,
        *,
        document_id: UUID,
        original_filename: str,
        mime_type: str,
        size_bytes: int,
        sha256: str,
        storage_reference: str,
        uploaded_at: datetime | None = None,
    ) -> Artifact:
        return cls(
            artifact_id=uuid4(),
            document_id=document_id,
            role=ArtifactRole.ORIGINAL,
            original_filename=original_filename,
            mime_type=mime_type,
            size_bytes=size_bytes,
            sha256=sha256,
            storage_reference=storage_reference,
            uploaded_at=uploaded_at or _utc_now(),
        )


@dataclass(frozen=True, slots=True)
class Document:
    document_id: UUID
    owner_id: str
    status: DocumentStatus
    created_at: datetime
    updated_at: datetime
    original_artifact_id: UUID | None = None

    def __post_init__(self) -> None:
        _require_text(self.owner_id, "owner_id")
        if self.created_at.tzinfo is None or self.updated_at.tzinfo is None:
            raise DomainError("document timestamps must be timezone-aware")

    @classmethod
    def create(cls, *, owner_id: str, document_id: UUID | None = None) -> Document:
        now = _utc_now()
        return cls(
            document_id=document_id or uuid4(),
            owner_id=owner_id,
            status=DocumentStatus.RECEIVED,
            created_at=now,
            updated_at=now,
        )

    def transition_to(self, status: DocumentStatus) -> Document:
        if status not in DOCUMENT_TRANSITIONS[self.status]:
            raise InvalidStateTransition(
                f"document cannot transition from {self.status} to {status}"
            )
        return replace(self, status=status, updated_at=_utc_now())

    def attach_original(self, artifact: Artifact) -> Document:
        if artifact.document_id != self.document_id or artifact.role != ArtifactRole.ORIGINAL:
            raise OriginalArtifactError("artifact must be this document's original artifact")
        if self.original_artifact_id is not None:
            raise OriginalArtifactError("a document can have only one original artifact")
        return replace(self, original_artifact_id=artifact.artifact_id, updated_at=_utc_now())


@dataclass(frozen=True, slots=True)
class ProcessingJob:
    job_id: UUID
    document_id: UUID
    original_artifact_id: UUID
    status: JobStatus
    retry_count: int
    last_error: str | None
    created_at: datetime
    updated_at: datetime

    def __post_init__(self) -> None:
        if self.retry_count < 0:
            raise DomainError("retry_count cannot be negative")
        if self.created_at.tzinfo is None or self.updated_at.tzinfo is None:
            raise DomainError("job timestamps must be timezone-aware")

    @classmethod
    def create(
        cls,
        *,
        document_id: UUID,
        original_artifact_id: UUID,
        job_id: UUID | None = None,
    ) -> ProcessingJob:
        now = _utc_now()
        return cls(
            job_id=job_id or uuid4(),
            document_id=document_id,
            original_artifact_id=original_artifact_id,
            status=JobStatus.QUEUED,
            retry_count=0,
            last_error=None,
            created_at=now,
            updated_at=now,
        )

    def transition_to(self, status: JobStatus, *, error: str | None = None) -> ProcessingJob:
        if status not in JOB_TRANSITIONS[self.status]:
            raise InvalidStateTransition(f"job cannot transition from {self.status} to {status}")
        retry_count = (
            self.retry_count + 1
            if self.status == JobStatus.FAILED and status == JobStatus.QUEUED
            else self.retry_count
        )
        return replace(
            self,
            status=status,
            retry_count=retry_count,
            last_error=error if status == JobStatus.FAILED else None,
            updated_at=_utc_now(),
        )


@dataclass(frozen=True, slots=True)
class OutboxMessage:
    """A durable, reference-only message waiting for broker publication."""

    outbox_id: UUID
    job_id: UUID
    document_id: UUID
    original_artifact_id: UUID
    routing_key: str
    attempts: int
    published_at: datetime | None
    created_at: datetime

    def __post_init__(self) -> None:
        if self.attempts < 0:
            raise DomainError("attempts cannot be negative")
        if self.created_at.tzinfo is None:
            raise DomainError("created_at must be timezone-aware")
        if self.published_at is not None and self.published_at.tzinfo is None:
            raise DomainError("published_at must be timezone-aware")

    @classmethod
    def for_job(cls, job: ProcessingJob, *, routing_key: str) -> OutboxMessage:
        return cls(
            outbox_id=uuid4(),
            job_id=job.job_id,
            document_id=job.document_id,
            original_artifact_id=job.original_artifact_id,
            routing_key=routing_key,
            attempts=0,
            published_at=None,
            created_at=_utc_now(),
        )
