"""Small, testable job-consumer policy for acknowledgements and retries."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from app.domain.models import JobStatus, ProcessingJob
from app.processing.contracts import PermanentProcessingError, RetryableProcessingError, retry_delay

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class DeliveryDecision:
    action: str  # ack, retry, dead_letter
    job: ProcessingJob
    delay_seconds: float = 0
    error: str | None = None


def decide_delivery(
    job: ProcessingJob,
    error: Exception | None,
    *,
    max_retries: int = 3,
    base_delay_seconds: float = 1,
    max_delay_seconds: float = 60,
) -> DeliveryDecision:
    active = job.transition_to(JobStatus.PROCESSING) if job.status == JobStatus.QUEUED else job
    if error is None:
        decision = DeliveryDecision("ack", active.transition_to(JobStatus.COMPLETED))
        logger.info("processing job completed", extra={"job_id": str(job.job_id)})
        return decision
    failed = active.transition_to(JobStatus.FAILED, error=str(error))
    if isinstance(error, PermanentProcessingError):
        logger.warning("processing job dead-lettered", extra={"job_id": str(job.job_id)})
        return DeliveryDecision("dead_letter", failed, error=str(error))
    if not isinstance(error, RetryableProcessingError) or job.retry_count >= max_retries:
        logger.warning("processing job retry exhausted", extra={"job_id": str(job.job_id)})
        return DeliveryDecision("dead_letter", failed, error=str(error))
    queued = failed.transition_to(JobStatus.QUEUED)
    decision = DeliveryDecision(
        "retry",
        queued,
        retry_delay(
            job.retry_count, base_seconds=base_delay_seconds, max_seconds=max_delay_seconds
        ),
        error=str(error),
    )
    logger.info("processing job scheduled for retry", extra={"job_id": str(job.job_id)})
    return decision


__all__ = ["DeliveryDecision", "decide_delivery"]
