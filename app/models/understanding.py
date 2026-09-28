"""Provider-neutral Document Representation value objects."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4


class ProcessingStatus(StrEnum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class BlockType(StrEnum):
    TEXT = "text"
    TABLE = "table"
    IMAGE = "image"


@dataclass(frozen=True, slots=True)
class ContentBlock:
    block_id: UUID = field(default_factory=uuid4)
    type: BlockType = BlockType.TEXT
    text: str = ""
    page_number: int | None = None
    reading_order: int | None = None
    bbox: tuple[float, float, float, float] | None = None
    source_reference: str | None = None

    def __post_init__(self) -> None:
        if self.page_number is not None and self.page_number < 1:
            raise ValueError("page_number must be positive")
        if self.reading_order is not None and self.reading_order < 0:
            raise ValueError("reading_order cannot be negative")
        if self.bbox is not None and len(self.bbox) != 4:
            raise ValueError("bbox must contain four coordinates")


@dataclass(frozen=True, slots=True)
class PageRepresentation:
    number: int
    width: float | None = None
    height: float | None = None
    blocks: tuple[ContentBlock, ...] = ()

    def __post_init__(self) -> None:
        if self.number < 1:
            raise ValueError("page number must be positive")


@dataclass(frozen=True, slots=True)
class ProcessingProvenance:
    processor: str
    processor_version: str
    logic_version: str
    artifact_id: UUID
    storage_reference: str
    processed_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        if self.processed_at.tzinfo is None:
            raise ValueError("processed_at must be timezone-aware")


@dataclass(frozen=True, slots=True)
class ProcessingFailure:
    code: str
    message: str
    retryable: bool
    attempt: int


@dataclass(frozen=True, slots=True)
class DocumentRepresentation:
    representation_id: UUID
    document_id: UUID
    artifact_id: UUID
    mime_type: str
    pages: tuple[PageRepresentation, ...]
    blocks: tuple[ContentBlock, ...]
    tables: tuple[ContentBlock, ...]
    images: tuple[ContentBlock, ...]
    provenance: ProcessingProvenance
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        if self.created_at.tzinfo is None:
            raise ValueError("created_at must be timezone-aware")
        if self.provenance.artifact_id != self.artifact_id:
            raise ValueError("provenance must reference the representation artifact")

    @property
    def text(self) -> str:
        return "\n".join(block.text for block in self.blocks if block.text)


__all__ = [
    "BlockType",
    "ContentBlock",
    "DocumentRepresentation",
    "PageRepresentation",
    "ProcessingFailure",
    "ProcessingProvenance",
    "ProcessingStatus",
]
