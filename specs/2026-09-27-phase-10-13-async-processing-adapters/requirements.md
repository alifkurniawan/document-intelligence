# Phases 10–13 Feature Specification — Async Processing Adapters

## Context

Phases 10–13 extend the completed single-document ingestion slice with a durable RabbitMQ hand-off, operational job processing behavior, a reusable batch/import adapter, and technical normalization only when a concrete downstream need exists. This specification follows the [mission](../mission.md), [roadmap](../roadmap.md), and [tech stack](../tech-stack.md). The original artifact remains immutable source of truth; downstream understanding is out of scope.

## Scope

The implementation must provide:

1. A RabbitMQ publisher adapter with one durable MVP processing queue, documented message schema, publisher confirms, retry policy, DLQ, and configuration.
2. A consumer-facing job contract covering queued, processing, completed, and failed states, acknowledgement rules, bounded retry, and dead-letter behavior where required.
3. The contracts and extension points for a future batch/import adapter, without implementing batch/import in L2.1.
4. A normalization decision record stating that normalization is not required and is not mandatory in L2.1.

## Confirmed constraints

* Messages contain `document_id`, `job_id`, and minimum execution metadata only; never binary content.
* A message must not direct a consumer to an uncommitted document, missing original, or incomplete artifact metadata.
* Upload responses do not wait for downstream processing.
* The original artifact is never overwritten or replaced by normalization.
* Single-document upload is the only implemented entry point in L2.1. Batch/import is deferred.
* `document_id` is the primary idempotency reference for the current single-document workflow. A dedicated idempotency key will be defined when batch/import is introduced.
* MVP RabbitMQ uses one main processing queue, exponential backoff with three retries, then a dead-letter queue.
* Permanent validation errors are not retried; retryable failures remain bounded, observable, and safe to repeat.
* PostgreSQL-to-RabbitMQ coordination uses an outbox pattern so committed jobs cannot silently lose their processing message.
* Provider-specific RabbitMQ, storage, and database behavior remains behind application-facing ports.
* Configuration and credentials come from environment-backed settings.
* No OCR, semantic extraction, classification, legal analysis, or automatic universal format conversion is included.

## Decisions requiring confirmation

All initial planning decisions are confirmed: phases 10–13 remain combined unless implementation complexity justifies a split; normalization is deferred and not mandatory in L2.1; RabbitMQ uses one main processing queue with three exponential-backoff retries and a DLQ; batch/import is deferred; `document_id` is the current idempotency reference; and an outbox coordinates PostgreSQL commits with message publication.

## Non-goals

Do not add document understanding, OCR, semantic metadata, batch/import implementation, unbounded concurrency, silent message loss, or normalization without an accepted concrete requirement.
