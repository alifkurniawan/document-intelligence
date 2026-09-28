"""Reference-only worker for Document Understanding jobs."""

from __future__ import annotations

from app.services.document_understanding import DocumentUnderstandingService
from app.workers.contracts import (
    PermanentProcessingError,
    ProcessingMessage,
    RetryableProcessingError,
)
from app.workers.processing import DeliveryDecision, decide_delivery


class DocumentUnderstandingWorker:
    """Execute one message and persist lifecycle/result changes atomically."""

    def __init__(
        self,
        *,
        unit_of_work_factory,
        understanding_service: DocumentUnderstandingService,
        max_retries: int = 3,
        base_delay_seconds: float = 1,
        max_delay_seconds: float = 60,
    ) -> None:
        self.unit_of_work_factory = unit_of_work_factory
        self.understanding_service = understanding_service
        self.max_retries = max_retries
        self.base_delay_seconds = base_delay_seconds
        self.max_delay_seconds = max_delay_seconds

    async def handle(self, message: ProcessingMessage) -> DeliveryDecision:
        async with self.unit_of_work_factory() as unit_of_work:
            job = await unit_of_work.jobs.get(message.job_id)
            if job is None:
                raise PermanentProcessingError("processing job was not found")
            if (
                job.document_id != message.document_id
                or job.original_artifact_id != message.original_artifact_id
            ):
                raise PermanentProcessingError("processing message references do not match the job")

            artifact = await unit_of_work.artifacts.get(job.original_artifact_id)
            if artifact is None:
                error: Exception = PermanentProcessingError("original artifact was not found")
                decision = decide_delivery(
                    job,
                    error,
                    max_retries=self.max_retries,
                    base_delay_seconds=self.base_delay_seconds,
                    max_delay_seconds=self.max_delay_seconds,
                )
            else:
                outcome = await self.understanding_service.process(
                    document_id=job.document_id, artifact=artifact, attempt=message.attempt
                )
                if outcome.failure is None:
                    error = None
                elif outcome.failure.retryable:
                    error = RetryableProcessingError(outcome.failure.message)
                else:
                    error = PermanentProcessingError(outcome.failure.message)
                decision = decide_delivery(
                    job,
                    error,
                    max_retries=self.max_retries,
                    base_delay_seconds=self.base_delay_seconds,
                    max_delay_seconds=self.max_delay_seconds,
                )
                if outcome.representation is not None:
                    await unit_of_work.representations.add(outcome.representation)

            await unit_of_work.jobs.update(decision.job)
            await unit_of_work.commit()
            return decision


__all__ = ["DocumentUnderstandingWorker"]
