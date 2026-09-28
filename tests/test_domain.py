from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.core.errors import DomainError, InvalidStateTransition, OriginalArtifactError
from app.models.entities import Artifact, Document, DocumentStatus, JobStatus, ProcessingJob


def test_document_lifecycle_and_original_artifact_are_provider_neutral() -> None:
    document = Document.create(owner_id="account-1")
    document = document.transition_to(DocumentStatus.VALIDATING)
    document = document.transition_to(DocumentStatus.REGISTERED)
    artifact = Artifact.create_original(
        document_id=document.document_id,
        original_filename="contract.pdf",
        mime_type="application/pdf",
        size_bytes=10,
        sha256="a" * 64,
        storage_reference="documents/one/original",
    )

    document = document.attach_original(artifact)

    assert document.original_artifact_id == artifact.artifact_id
    assert document.status is DocumentStatus.REGISTERED


def test_document_rejects_invalid_transitions_and_duplicate_originals() -> None:
    document = Document.create(owner_id="account-1")
    artifact = Artifact.create_original(
        document_id=document.document_id,
        original_filename="contract.pdf",
        mime_type="application/pdf",
        size_bytes=10,
        sha256="a" * 64,
        storage_reference="documents/one/original",
    )

    with pytest.raises(InvalidStateTransition):
        document.transition_to(DocumentStatus.QUEUED)

    attached = document.attach_original(artifact)
    with pytest.raises(OriginalArtifactError):
        attached.attach_original(artifact)


def test_processing_job_requires_an_original_reference_and_supports_retry_transition() -> None:
    document_id = uuid4()
    artifact_id = uuid4()
    job = ProcessingJob.create(document_id=document_id, original_artifact_id=artifact_id)
    processing = job.transition_to(JobStatus.PROCESSING)
    failed = processing.transition_to(JobStatus.FAILED, error="temporary failure")
    retried = failed.transition_to(JobStatus.QUEUED)

    assert failed.last_error == "temporary failure"
    assert retried.retry_count == 1
    assert retried.last_error is None


def test_domain_rejects_naive_timestamps_and_empty_owner() -> None:
    with pytest.raises(DomainError):
        Document.create(owner_id="")

    with pytest.raises(DomainError):
        Artifact(
            artifact_id=uuid4(),
            document_id=uuid4(),
            role="original",
            original_filename="file.pdf",
            mime_type="application/pdf",
            size_bytes=1,
            sha256="a" * 64,
            storage_reference="ref",
            uploaded_at=datetime.now(UTC).replace(tzinfo=None),
        )
