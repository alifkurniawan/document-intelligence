"""Provider-neutral contracts for asynchronous document processing."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ProcessingMessage:
    document_id: UUID
    job_id: UUID
    original_artifact_id: UUID
    attempt: int = 0
    correlation_id: str | None = None
    enqueued_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def as_payload(self) -> dict[str, str | int]:
        return {
            "document_id": str(self.document_id),
            "job_id": str(self.job_id),
            "original_artifact_id": str(self.original_artifact_id),
            "attempt": self.attempt,
            "correlation_id": self.correlation_id or str(self.job_id),
            "enqueued_at": self.enqueued_at.isoformat(),
        }


class MessagePublisher:
    async def publish(self, message: ProcessingMessage, *, routing_key: str) -> None:
        raise NotImplementedError


class PermanentProcessingError(Exception):
    """The job is invalid and must be acknowledged without retry."""


class RetryableProcessingError(Exception):
    """A transient processing failure eligible for bounded retry."""


def retry_delay(attempt: int, *, base_seconds: float, max_seconds: float) -> float:
    """Return exponential delay for a zero-based retry attempt."""

    if attempt < 0:
        raise ValueError("attempt cannot be negative")
    return min(max_seconds, base_seconds * (2**attempt))


__all__ = [
    "MessagePublisher",
    "PermanentProcessingError",
    "ProcessingMessage",
    "RetryableProcessingError",
    "retry_delay",
]
