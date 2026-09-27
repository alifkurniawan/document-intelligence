# Phases 14–15 Feature Specification — Integration Testing and Error Recovery

## Context

Phases 14 and 15 verify the ingestion subsystem across its real infrastructure boundaries and make failures diagnosable and recoverable. This specification follows the [mission](../mission.md), [roadmap](../roadmap.md), and [tech stack](../tech-stack.md). It assumes the Phase 10–13 RabbitMQ/outbox contracts are available and preserves the original artifact as immutable source of truth.

The phases are combined because integration tests must exercise the same transaction, message, retry, ownership, and recovery behavior that production operations depend on.

## Scope

The implementation must provide:

1. A repeatable integration-test environment covering the API, PostgreSQL, storage adapter, RabbitMQ, authentication test double/emulator strategy, and relevant transaction boundaries.
2. Fixture documents and test utilities for supported inputs, invalid inputs, ownership isolation, duplicate delivery, retry, and failure scenarios.
3. End-to-end coverage for authenticated upload, validation, durable document/artifact/job registration, original retrieval, asynchronous hand-off, and observable status.
4. A consistent API error schema with correlation IDs and stable mappings for validation, authentication, authorization, not-found, conflict, dependency, and unexpected failures.
5. Structured logs and operational context sufficient to trace a request, document, job, outbox record, and recovery attempt without logging secrets or document bytes.
6. Orphan detection and reconciliation for records or artifacts left inconsistent by partial failure, with a safe, repeatable operator command or job.
7. Safe retry commands for eligible jobs/outbox records, with ownership, idempotency, bounded attempts, and audit context.
8. Metrics and alert definitions appropriate to the deployment, documented without requiring production credentials in tests.
9. A recovery runbook describing diagnosis, reconciliation, retry, dead-letter handling, and escalation.

## Confirmed constraints

* Tests must be runnable in CI or through documented local commands without production credentials.
* PostgreSQL and RabbitMQ-backed behavior must be tested against isolated services or equivalent deterministic environments; fakes remain appropriate for focused unit tests.
* Authentication tests use a test double or emulator and must still exercise authenticated and unauthenticated boundaries.
* Integration tests must prove ownership isolation, immutable originals, reference-only messages, transaction safety, duplicate/retry safety, and missing-dependency behavior.
* API errors are machine-readable and include a correlation identifier; internal exception details and secrets are not exposed to clients.
* Recovery actions are idempotent, bounded, authorized, and observable. They never overwrite an original artifact or fabricate successful processing state.
* Orphan reconciliation is explicit and auditable; it does not silently delete or mutate user-owned originals.
* Configuration and credentials come from environment-backed settings. Test fixtures contain no real credentials or sensitive documents.
* No OCR, semantic extraction, classification, legal analysis, or broad format conversion is introduced.

## Confirmed decisions

1. The first recovery release allows operator-triggered retries and reconciliation only. Metrics and alerts identify candidates; periodic automation is deferred until ownership and scheduling are agreed.
2. The integration suite uses isolated Docker Compose PostgreSQL and RabbitMQ services locally and in CI-capable environments. Focused unit/API tests remain deterministic and do not require external credentials.

## Non-goals

Do not add a new processing workflow, production credential dependency, silent cleanup, unbounded retry, automatic destructive repair, or document-understanding capability.
