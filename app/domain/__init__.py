"""Provider-neutral ingestion domain types."""

from app.domain.models import (
    Artifact,
    ArtifactRole,
    Document,
    DocumentStatus,
    JobStatus,
    ProcessingJob,
)

__all__ = [
    "Artifact",
    "ArtifactRole",
    "Document",
    "DocumentStatus",
    "JobStatus",
    "ProcessingJob",
]
