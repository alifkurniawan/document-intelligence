"""Application service coordinating validation, storage, and metadata registration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from app.domain.models import Artifact, Document, DocumentStatus, OutboxMessage, ProcessingJob
from app.ingestion.storage import ArtifactStorage
from app.ingestion.validation import FileValidator, ValidatedFile
from app.repositories.contracts import MetadataUnitOfWork


@dataclass(frozen=True, slots=True)
class RegistrationResult:
    document: Document
    artifact: Artifact
    job: ProcessingJob


class DocumentRegistrationService:
    def __init__(
        self,
        *,
        validator: FileValidator,
        storage: ArtifactStorage,
        unit_of_work_factory: Callable[[], MetadataUnitOfWork],
        routing_key: str = "document.process",
    ) -> None:
        self.validator = validator
        self.storage = storage
        self.unit_of_work_factory = unit_of_work_factory
        self.routing_key = routing_key

    async def register(
        self, *, owner_id: str, filename: str | None, client_mime: str | None, source
    ) -> RegistrationResult:
        validated: ValidatedFile = self.validator.validate(
            filename=filename, client_mime=client_mime, source=source
        )
        document = Document.create(owner_id=owner_id)
        stored = None
        try:
            stored = await self.storage.store(
                document_id=document.document_id,
                filename=validated.filename,
                source=validated.stream,
                expected_size=validated.size_bytes,
                expected_sha256=validated.sha256,
            )
            artifact = Artifact.create_original(
                document_id=document.document_id,
                original_filename=validated.filename,
                mime_type=validated.mime_type,
                size_bytes=stored.size_bytes,
                sha256=stored.sha256,
                storage_reference=stored.storage_reference,
                uploaded_at=stored.stored_at,
            )
            document = document.transition_to(DocumentStatus.VALIDATING)
            document = document.transition_to(DocumentStatus.REGISTERED).attach_original(artifact)
            document = document.transition_to(DocumentStatus.STORED)
            document = document.transition_to(DocumentStatus.QUEUED)
            job = ProcessingJob.create(
                document_id=document.document_id,
                original_artifact_id=artifact.artifact_id,
            )
            async with self.unit_of_work_factory() as unit_of_work:
                await unit_of_work.documents.add(document)
                await unit_of_work.artifacts.add(artifact)
                await unit_of_work.jobs.add(job)
                # Older in-memory test doubles may not expose the phase-10 port.
                if hasattr(unit_of_work, "outbox"):
                    await unit_of_work.outbox.add(
                        OutboxMessage.for_job(job, routing_key=self.routing_key)
                    )
                await unit_of_work.commit()
            return RegistrationResult(document=document, artifact=artifact, job=job)
        except Exception:
            if stored is not None:
                try:
                    await self.storage.delete(stored.storage_reference)
                except Exception:
                    pass
            raise
        finally:
            validated.close()
