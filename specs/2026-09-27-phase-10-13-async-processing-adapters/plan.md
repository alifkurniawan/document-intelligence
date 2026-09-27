# Phases 10–13 Implementation Plan — Async Processing Adapters

## Task group 1 — Confirm contracts and decisions

1. Record that phases 10–13 remain one combined branch/spec unless implementation complexity justifies a split.
2. Define the broker message, consumer job, retry, dead-letter, and current single-document idempotency contracts.
3. Define the future batch/import extension point without implementing batch/import in L2.1.
4. Record that normalization is deferred because no concrete downstream requirement exists.
5. Choose and document the outbox coordination strategy and its recovery boundary.
6. Map the contracts to the existing domain, repositories, configuration, and single-document service.

## Task group 2 — Implement RabbitMQ integration

1. Add configuration for broker URL, one durable processing queue, routing, publisher confirms, exponential retry settings, DLQ, and delivery settings.
2. Add an application-facing publisher port and RabbitMQ adapter with durable declarations.
3. Publish reference-only messages containing `document_id`, `job_id`, and required execution metadata.
4. Persist an outbox record in the same database transaction as the job and publish from the outbox reliably.
5. Ensure publication occurs only for durably resolvable jobs and define failure/recovery behavior.
6. Add contract tests for message shape, confirms, configuration, outbox recovery, and absence of binary data.

## Task group 3 — Implement asynchronous job hand-off

1. Define legal job-state transitions and persistence behavior for queued, processing, completed, and failed states.
2. Implement consumer acknowledgement, exponential backoff with three retries, redelivery, and DLQ handling.
3. Preserve the original failure context while making permanent failure visible and queryable.
4. Add correlation identifiers and structured operational events at the broker/application boundary.
5. Test transient failure, permanent failure, duplicate delivery, acknowledgement failure, and recovery paths.

## Task group 4 — Reserve the batch/import extension point

1. Document the future adapter input, per-item result model, cancellation behavior, and bounded concurrency requirements.
2. Document that a dedicated idempotency key will be introduced when batch/import is implemented.
3. Add no batch/import runtime path or separate business workflow in L2.1.

## Task group 5 — Defer normalization

1. Record that no concrete downstream compatibility need currently exists.
2. Mark phase 13 deferred and add no normalizer in L2.1.
3. Preserve the original-artifact boundary so a future normalizer cannot overwrite the source of truth.

## Task group 6 — Verify and prepare for handoff

1. Run unit, contract, API, database, and RabbitMQ-backed integration tests appropriate to the chosen strategy.
2. Verify upload returns before downstream completion and every accepted job is traceable to durable metadata.
3. Verify retry/dead-letter behavior, batch isolation, idempotency, ownership, and original-artifact immutability.
4. Update configuration examples, operational runbook, migrations, and architecture/decision records.
5. Run Ruff formatting/linting and the full test suite; resolve all open decisions before merge.
