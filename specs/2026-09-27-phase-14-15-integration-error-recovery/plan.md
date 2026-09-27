# Phases 14–15 Implementation Plan — Integration Testing and Error Recovery

## Task group 1 — Confirm contracts and test topology

1. Confirmed operator-triggered recovery and isolated Docker Compose service topology; periodic reconciliation remains deferred.
2. Inventory existing API, domain, repository, storage, broker, outbox, authentication, and configuration seams.
3. Define correlation-ID propagation across HTTP, logs, database records where needed, outbox entries, and RabbitMQ messages.
4. Define the error taxonomy, public response schema, retryability classification, and redaction rules.

## Task group 2 — Build repeatable integration infrastructure

1. Provide isolated PostgreSQL, RabbitMQ, storage, and authentication test-double/emulator setup.
2. Add deterministic fixture documents for supported, malformed, oversized, unreadable, duplicate, and ownership-isolation cases.
3. Add setup/teardown utilities that apply migrations, declare broker resources, clean test data, and avoid production credentials.
4. Document local and CI commands, prerequisites, service lifecycle, and troubleshooting.

## Task group 3 — Implement end-to-end integration coverage

1. Test authenticated upload through durable registration, immutable original retrieval, job creation, outbox publication, and status observation.
2. Test validation failures, unauthenticated access, authorization failures, not-found behavior, and dependency failures.
3. Test transaction rollback and crash-window scenarios so no consumer receives an unusable reference.
4. Test duplicate requests/delivery, bounded retries, dead-letter behavior, acknowledgement failure, and safe reprocessing.
5. Test ownership isolation across every document, artifact, job, and recovery operation.

## Task group 4 — Standardize diagnostics and errors

1. Implement the consistent API error envelope and status mapping without leaking internal details.
2. Generate or propagate correlation IDs and include document/job identifiers only where safe and useful.
3. Emit structured logs for acceptance, rejection, publication, retry, reconciliation, and terminal failure.
4. Add metrics and alert thresholds for validation failures, dependency failures, orphan candidates, retry exhaustion, queue/DLQ growth, and reconciliation outcomes.

## Task group 5 — Implement recovery and reconciliation

1. Define detectable orphan and inconsistent-state classes with conservative eligibility rules.
2. Implement a dry-run-capable reconciliation command or job that reports candidates and records its result.
3. Implement safe retry commands for eligible outbox records/jobs with bounded attempts and idempotency protection.
4. Ensure recovery never overwrites originals, bypasses ownership checks, or marks work complete without durable evidence.
5. Add tests for repeated recovery, partial recovery, missing dependencies, concurrent operators, and permanent failures.

## Task group 6 — Document and verify the release

1. Write the recovery runbook with diagnosis, commands, expected outputs, rollback/stop conditions, and escalation paths.
2. Add configuration and operational documentation for correlation IDs, metrics, alerts, test services, and recovery limits.
3. Run unit, API, database, storage, RabbitMQ, and full integration suites in the documented environment.
4. Run Ruff formatting/linting and verify migrations and clean-environment setup.
5. Resolve all open decisions and review security, ownership, observability, and original-artifact invariants before merge.
