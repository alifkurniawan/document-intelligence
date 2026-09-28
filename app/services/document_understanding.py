"""Document Understanding business workflows."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from uuid import UUID, uuid4

from app.models.entities import Artifact
from app.models.understanding import (
    BlockType,
    DocumentRepresentation,
    ProcessingFailure,
    ProcessingProvenance,
    ProcessingStatus,
)
from app.services.document_processors import (
    DOCXProcessor,
    ImageOCRProcessor,
    PDFProcessor,
    ProcessorResult,
    ProcessorUnavailable,
    XLSXProcessor,
)
from app.storage.artifacts import ArtifactStorage


@dataclass(frozen=True, slots=True)
class ProcessingOutcome:
    status: ProcessingStatus
    representation: DocumentRepresentation | None = None
    failure: ProcessingFailure | None = None


class UnsupportedDocumentError(ValueError):
    pass


class DocumentUnderstandingService:
    """Read an immutable original and create a new derived representation."""

    def __init__(
        self,
        *,
        storage: ArtifactStorage,
        processors: dict[str, object] | None = None,
        logic_version: str = "1",
    ) -> None:
        self.storage = storage
        self.processors = processors or {
            "application/pdf": PDFProcessor(),
            "image/jpeg": ImageOCRProcessor(),
            "image/png": ImageOCRProcessor(),
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document": (
                DOCXProcessor()
            ),
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": XLSXProcessor(),
        }
        self.logic_version = logic_version

    def select_processor(self, artifact: Artifact) -> object:
        try:
            return self.processors[artifact.mime_type.lower()]
        except KeyError as exc:
            raise UnsupportedDocumentError(
                f"no processor for MIME type {artifact.mime_type}"
            ) from exc

    async def process(
        self, *, document_id: UUID, artifact: Artifact, attempt: int = 0
    ) -> ProcessingOutcome:
        if artifact.document_id != document_id:
            raise PermissionError("artifact does not belong to document")
        try:
            processor = self.select_processor(artifact)
            result: ProcessorResult = await asyncio.to_thread(
                processor.process, await self.storage.read(artifact.storage_reference)
            )
            provenance = ProcessingProvenance(
                processor=processor.name,
                processor_version=getattr(processor, "version", "unknown"),
                logic_version=self.logic_version,
                artifact_id=artifact.artifact_id,
                storage_reference=artifact.storage_reference,
            )
            representation = DocumentRepresentation(
                representation_id=uuid4(),
                document_id=document_id,
                artifact_id=artifact.artifact_id,
                mime_type=artifact.mime_type,
                pages=result.pages,
                blocks=result.blocks,
                tables=tuple(block for block in result.blocks if block.type is BlockType.TABLE),
                images=tuple(block for block in result.blocks if block.type is BlockType.IMAGE),
                provenance=provenance,
            )
            return ProcessingOutcome(ProcessingStatus.COMPLETED, representation=representation)
        except ProcessorUnavailable as exc:
            return ProcessingOutcome(
                ProcessingStatus.FAILED,
                failure=ProcessingFailure("processor_unavailable", str(exc), True, attempt),
            )
        except (ValueError, OSError) as exc:
            return ProcessingOutcome(
                ProcessingStatus.FAILED,
                failure=ProcessingFailure("invalid_document", str(exc), False, attempt),
            )
        except Exception as exc:
            return ProcessingOutcome(
                ProcessingStatus.FAILED,
                failure=ProcessingFailure("processing_failed", str(exc), True, attempt),
            )

    async def reprocess(
        self, *, document_id: UUID, artifact: Artifact, attempt: int = 0
    ) -> ProcessingOutcome:
        return await self.process(document_id=document_id, artifact=artifact, attempt=attempt)


__all__ = ["DocumentUnderstandingService", "ProcessingOutcome", "UnsupportedDocumentError"]
