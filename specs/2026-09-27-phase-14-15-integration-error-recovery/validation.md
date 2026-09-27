# Phases 14–15 Validation and Merge Criteria

## Automated checks

1. Ruff formatting and linting pass.
2. The full pytest suite passes.
3. A clean environment can apply migrations and run the documented integration suite without production credentials.
4. Integration services are isolated, repeatable, and cleaned between tests.

## End-to-end behavior

1. Authenticated upload completes through validation, durable document/artifact/job registration, original retrieval, outbox publication, and observable queued status.
2. Invalid files produce deterministic public errors; authentication, authorization, not-found, conflict, and dependency failures map to the documented schema.
3. PostgreSQL rollback, storage failure, broker failure, duplicate delivery, acknowledgement failure, retry exhaustion, and DLQ behavior are covered.
4. No message, log, database row, or error response contains binary document contents, secrets, or unredacted provider credentials.
5. Ownership isolation is proven for reads, downloads, status, retries, reconciliation, and administrative boundaries.
6. Original artifacts remain independently retrievable, immutable, and the source of truth after retries and recovery.

## Diagnostics and recovery

1. Correlation IDs are present or safely propagated across API responses, structured logs, and asynchronous job events.
2. Metrics and alert definitions cover failure rate, dependency health, retry/DLQ growth, orphan candidates, and recovery outcomes.
3. Orphan detection is conservative, repeatable, auditable, and has a dry-run or equivalent preview path.
4. Retry and reconciliation actions are authorized, bounded, idempotent, observable, and safe to repeat concurrently.
5. Recovery never silently deletes originals, fabricates completion, or bypasses durable state transitions.
6. The recovery runbook is sufficient for an operator to diagnose and execute safe actions in a non-production test environment.

## Merge decision

Merge is allowed when the confirmed requirements, isolated integration suite, error/observability checks, recovery tests, runbook, configuration documentation, and security/ownership review pass with no unrelated changes.
