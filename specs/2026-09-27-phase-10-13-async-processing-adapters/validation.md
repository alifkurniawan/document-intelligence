# Phases 10–13 Validation and Merge Criteria

## Automated checks

1. Ruff formatting and linting pass.
2. The full pytest suite passes.
3. Clean migrations apply and relevant PostgreSQL/RabbitMQ integration tests pass without production credentials.
4. Fakes or local services deterministically cover publisher confirms, redelivery, retry, and dead-letter behavior.

## RabbitMQ and job behavior

1. Exchanges and queues are durable and match documented configuration.
2. Messages contain references and required execution metadata only; no binary data appears in messages, logs, or database records.
3. Every published message resolves to a persisted document, original artifact, and job.
4. The outbox record is committed atomically with the job and reliably retried until publication succeeds or is operationally surfaced.
5. Upload returns after durable registration/hand-off initiation and never waits for downstream completion.
6. Legal state transitions are enforced; acknowledgements, three exponential-backoff retries, DLQ routing, and permanent failures are observable and tested.
7. Permanent validation errors are not retried.
8. Duplicate delivery and retry do not create unsafe duplicate processing or overwrite originals.

## Deferred batch/import behavior

1. No batch/import runtime path is introduced in L2.1.
2. The future adapter contract states that it must reuse the single-document workflow.
3. `document_id` remains the current single-document idempotency reference; a dedicated batch/import key is deferred.

## Deferred normalization boundary

1. Phase 13 is explicitly deferred because no concrete downstream requirement exists.
2. No normalizer is mandatory or implemented in L2.1.
3. Original artifacts remain independently retrievable, immutable, and the source of truth.
4. No OCR, semantic extraction, classification, legal analysis, or broad automatic conversion is introduced.

## Merge decision

Merge is allowed when the confirmed requirements, broker contract tests, state/retry/recovery tests, deferred batch/import boundary checks, configuration/runbook updates, and architecture/security review pass with no unrelated changes.
