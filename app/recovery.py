"""Conservative, operator-triggered recovery contracts.

Recovery is intentionally a reporting and retry boundary.  It never deletes
artifacts, fabricates completion, or bypasses the normal outbox publisher.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID, uuid4

from sqlalchemy import select

from app.domain.models import DocumentStatus
from app.infrastructure.database.models import ArtifactModel, DocumentModel, ProcessingJobModel
from app.observability import metrics


@dataclass(frozen=True, slots=True)
class RecoveryCandidate:
    kind: str
    identifier: UUID
    reason: str


@dataclass(frozen=True, slots=True)
class RecoveryReport:
    run_id: UUID
    dry_run: bool
    candidates: tuple[RecoveryCandidate, ...]
    retried: int = 0
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class RecoverySource(Protocol):
    async def find_candidates(self, *, limit: int) -> list[RecoveryCandidate]: ...


class RecoveryService:
    """Run a bounded, repeatable reconciliation preview or action.

    The source owns the conservative eligibility query.  The default action is
    a dry run; a concrete retry callback may only re-submit durable outbox rows.
    """

    def __init__(self, source: RecoverySource, retry_pending) -> None:
        self.source = source
        self.retry_pending = retry_pending

    async def reconcile(
        self, *, dry_run: bool = True, limit: int = 100, operator_id: str = "operator"
    ) -> RecoveryReport:
        if limit < 1 or limit > 1000:
            raise ValueError("limit must be between 1 and 1000")
        if not operator_id.strip():
            raise ValueError("operator_id is required")
        candidates = tuple(await self.source.find_candidates(limit=limit))
        retried = 0
        if not dry_run and candidates:
            retried = await self.retry_pending(candidates, operator_id=operator_id)
        metrics.increment("recovery_candidates", len(candidates))
        metrics.increment("recovery_runs")
        if retried:
            metrics.increment("recovery_retried", retried)
        return RecoveryReport(uuid4(), dry_run, candidates, retried)


class SqlAlchemyRecoverySource:
    """Read-only conservative orphan detection for an operator run."""

    def __init__(self, session_factory) -> None:
        self.session_factory = session_factory

    async def find_candidates(self, *, limit: int) -> list[RecoveryCandidate]:
        async with self.session_factory() as session:
            candidates: list[RecoveryCandidate] = []
            rows = await session.execute(
                select(DocumentModel.document_id)
                .outerjoin(
                    ArtifactModel,
                    (ArtifactModel.document_id == DocumentModel.document_id)
                    & (ArtifactModel.role == "original"),
                )
                .where(
                    DocumentModel.status.in_(
                        [DocumentStatus.STORED.value, DocumentStatus.QUEUED.value]
                    ),
                    ArtifactModel.artifact_id.is_(None),
                )
                .limit(limit)
            )
            candidates.extend(
                RecoveryCandidate(
                    "document_without_original",
                    row[0],
                    "document has no original artifact",
                )
                for row in rows
            )
            remaining = max(0, limit - len(candidates))
            if remaining:
                rows = await session.execute(
                    select(ProcessingJobModel.job_id)
                    .outerjoin(
                        DocumentModel,
                        ProcessingJobModel.document_id == DocumentModel.document_id,
                    )
                    .where(DocumentModel.document_id.is_(None))
                    .limit(remaining)
                )
                candidates.extend(
                    RecoveryCandidate("job_without_document", row[0], "job has no document")
                    for row in rows
                )
            return candidates


__all__ = ["RecoveryCandidate", "RecoveryReport", "RecoveryService", "SqlAlchemyRecoverySource"]
