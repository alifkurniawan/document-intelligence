import asyncio
from uuid import uuid4

import pytest

from app.recovery import RecoveryCandidate, RecoveryService


class FakeRecoverySource:
    async def find_candidates(self, *, limit: int):
        return [RecoveryCandidate("document_without_original", uuid4(), "missing original")][:limit]


def test_recovery_defaults_to_dry_run_and_is_bounded():
    retried = []

    async def retry(candidates, *, operator_id):
        retried.extend(candidates)
        return len(candidates)

    service = RecoveryService(FakeRecoverySource(), retry)
    report = asyncio.run(service.reconcile())

    assert report.dry_run is True
    assert report.retried == 0
    assert retried == []

    report = asyncio.run(service.reconcile(dry_run=False, operator_id="ops-1"))
    assert report.retried == 1
    assert len(retried) == 1

    with pytest.raises(ValueError):
        asyncio.run(service.reconcile(limit=1001))
