# Phase 4 Feature Specification — Domain Model

## Context

Phase 4 defines provider-neutral ingestion vocabulary before persistence and API workflows are built. It follows the database vocabulary established by Phase 3 but must remain independent of SQLAlchemy and all external providers. The [mission](../mission.md) requires immutable original provenance, authenticated ownership, asynchronous job references, and a strict boundary from Document Understanding.

## Scope

The implementation must provide:

1. Domain types for `Document`, `Artifact`, `ProcessingJob`, and authenticated owner identity.
2. Original-artifact metadata and provenance invariants.
3. Provider-neutral processing states, valid transitions, and domain errors.
4. Ownership checks and immutable-original behavior.
5. Pure unit tests that do not require PostgreSQL, Firebase, RabbitMQ, SQLAlchemy, or FastAPI.

## Proposed domain vocabulary

* `Document`: logical record with unique `document_id`, owner, lifecycle status, and timestamps.
* `Artifact`: physical file reference with artifact ID, document ID, role, filename, MIME type, byte size, SHA-256, storage reference, and upload time.
* `ProcessingJob`: durable job reference with `job_id`, document ID, status, retry information, and timestamps.
* `Owner`: stable authenticated account identifier; Firebase-specific token details stay outside the domain.
* Original artifact role: the source-of-truth artifact is immutable and cannot be replaced by derivatives or processing.

## Confirmed decisions

* Use application-generated UUIDs for document, artifact, and job identifiers.
* Use timezone-aware UTC timestamps.
* Represent lifecycle states as explicit enums rather than free-form strings.
* Use separate document and processing-job status enums.
* Keep `received`, `validating`, `registered`, `stored`, and `queued` as ingestion-owned document states; `processing`, `completed`, and `failed` remain downstream-visible job states where applicable.
* Model retry count and last error as job metadata, not as a new semantic state.
* A document has exactly one immutable original artifact and may have zero or more technical derivatives.
* Defer technical metadata such as page count until normalization is required.

## Constraints and non-goals

* Do not import SQLAlchemy or define ORM models in the domain package.
* Do not implement storage, file validation, authentication token verification, message publishing, OCR, classification, extraction, legal analysis, or Shariah analysis.
* Do not mutate original filename, MIME type, size, hash, upload time, owner, or storage reference after acceptance.

## Deferred implementation details

Retry transition commands and the exact owner value-object shape should be finalized during implementation, while preserving provider neutrality and explicit authorization checks.

## Future compatibility

Repositories map these domain types to SQLAlchemy models without leaking ORM instances. Application services will own orchestration and transaction boundaries, while APIs will map domain errors to HTTP responses.
