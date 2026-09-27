# Roadmap

The roadmap is intentionally incremental. Each phase should be independently reviewable and testable. The single-document workflow is the MVP core; batch/import is planned as an adapter that reuses it.

## Phase 1 — Project foundation — Complete

**Objective:** Establish a runnable, maintainable Python service.

**Scope:** Application package layout, FastAPI entry point, dependency management, health endpoint, baseline logging, test layout, and CI-quality commands.

**Deliverables:** Minimal service, `pyproject.toml` configuration, test harness, README development commands.

**Dependencies:** None.

**Acceptance criteria:** Service starts from documented commands, health check works, and an empty baseline test suite runs.

## Phase 2 — Configuration — Complete

**Objective:** Centralize environment-driven settings.

**Scope:** Typed settings, `.env.example`, environment validation, limits, allowlists, Firebase, PostgreSQL, RabbitMQ, and storage settings.

**Deliverables:** Settings module and configuration documentation.

**Dependencies:** Phase 1.

**Acceptance criteria:** No secrets or connection strings are hard-coded; missing required production settings fail clearly.

## Phase 3 — Database setup — Complete

**Objective:** Make metadata persistence reproducible.

**Scope:** PostgreSQL connection/session management, SQLAlchemy base, Alembic, initial migration wiring.

**Deliverables:** Migration commands and database integration tests.

**Dependencies:** Phase 2.

**Acceptance criteria:** A clean database can be migrated up and application sessions can be opened and closed safely.

## Phase 4 — Domain model — Complete

**Objective:** Define provider-neutral ingestion concepts.

**Scope:** Document, Artifact, ProcessingJob, authenticated owner, processing states, invariants, and domain errors.

**Deliverables:** Domain types and unit tests.

**Dependencies:** Phase 1; database vocabulary from Phase 3.

**Acceptance criteria:** Domain tests cover ownership, immutable original semantics, valid states, and invalid transitions without importing Firebase or SQLAlchemy.

## Phase 5 — Repository layer — Complete

**Objective:** Persist documents, artifacts, and jobs behind stable interfaces.

**Scope:** Repository contracts, SQLAlchemy implementations, constraints, indexes, and transaction boundaries.

**Deliverables:** Repositories and migration updates.

**Dependencies:** Phases 3–4.

**Acceptance criteria:** Metadata can be created, queried by owner/document ID, and rolled back atomically in integration tests.

## Phase 6 — File storage abstraction — Complete (MVP)

**Objective:** Preserve original binaries outside PostgreSQL.

**Scope:** Artifact storage port, Firebase Storage adapter, test/local adapter, immutable document-scoped paths, streaming upload, hash/size verification.

**Deliverables:** Storage interface and adapter tests.

**Dependencies:** Phases 2 and 4.

**Acceptance criteria:** Originals are stored without overwrite, storage references are returned, and stored bytes can be verified by SHA-256.

## Phase 7 — File validation — Complete (MVP)

**Objective:** Reject invalid inputs before acceptance.

**Scope:** Extension/MIME allowlist, size limit, readability/integrity checks, safe filename handling, and conservative format-specific checks for PDF, images, DOCX, and XLSX.

**Deliverables:** Validation service and error contract.

**Dependencies:** Phases 2 and 6.

**Acceptance criteria:** Supported valid files pass; mismatches, oversize, unreadable, corrupt, and unsupported files produce deterministic errors; no semantic extraction occurs.

## Phase 8 — Document registration — Complete (MVP)

**Objective:** Create a durable document/artifact/job model for an accepted input.

**Scope:** Registration application service, ownership, metadata, original-artifact record, and queued processing state.

**Deliverables:** Service orchestration and transaction tests.

**Dependencies:** Phases 4–7.

**Acceptance criteria:** Successful registration has a unique document ID, complete original metadata, and no accepted record exists without a resolvable original.

## Phase 9 — Single-document upload API — Complete (MVP)

**Objective:** Expose the first end-to-end ingestion workflow.

**Scope:** Firebase email-auth token verification, ownership authorization, multipart upload, request/response schemas, status codes, and document information response.

**Deliverables:** Upload endpoint and OpenAPI examples.

**Dependencies:** Phases 2 and 8.

**Acceptance criteria:** An authenticated user can upload one supported document and receive `document_id`, original metadata, uploader/time metadata, and queued status without downstream processing delay.

Production hardening follow-ups remain for atomic Firebase non-overwrite semantics,
Firebase SDK initialization, true streaming storage, stronger PDF integrity checks,
and final error-schema alignment.

## Phase 10 — RabbitMQ integration — Complete

**Objective:** Publish durable processing job references.

**Scope:** Exchange/queue topology, publisher adapter, message schema containing `document_id` and `job_id`, publisher confirms, and configuration.

**Deliverables:** RabbitMQ adapter and contract tests.

**Dependencies:** Phases 5 and 8.

**Acceptance criteria:** No binary data appears in messages; messages are traceable to a persisted job and use documented delivery settings.

Implemented with durable exchange/queue/DLQ declarations, publisher confirms, reference-only messages, environment-backed settings, and a transactional outbox.

## Phase 11 — Asynchronous processing hand-off — Complete

**Objective:** Make job state and retry behavior operationally safe.

**Scope:** Consumer-facing job contract, queued/processing/completed/failed states, acknowledgement rules, bounded retry, and dead-letter handling where needed.

**Deliverables:** Job manager behavior, state-transition tests, and runbook.

**Dependencies:** Phase 10.

**Acceptance criteria:** Upload returns before processing completion; transient failures can retry; permanent failures are visible and do not silently lose the original.

Implemented with provider-neutral processing contracts, legal job transitions, bounded exponential retry policy, and dead-letter decisions.

## Phase 12 — Batch/import adapter — Deferred

**Objective:** Add alternate entry points without duplicating ingestion rules.

**Scope:** Batch/import adapter contract, per-item result model, bounded concurrency, idempotency strategy, and reuse of the single-document service.

**Deliverables:** Adapter interface and focused tests. A separate batch API is added only if an actual caller requires it.

**Dependencies:** Phase 9; Phase 11 for job behavior.

**Acceptance criteria:** Each item follows the same validation, ownership, storage, registration, and job workflow; one failed item does not corrupt other items; no new domain semantics are introduced.

Deferred until a concrete caller exists. The future adapter must reuse the single-document workflow, use bounded concurrency, isolate per-item failures, and introduce a dedicated idempotency key.

## Phase 13 — Normalization, only when required — Deferred

**Objective:** Add technical normalization only for a demonstrated downstream compatibility need.

**Scope:** Basic property inspection or a specific format adapter, with explicit decision record and artifact lineage.

**Deliverables:** Small, justified normalizer and tests, if required.

**Dependencies:** A concrete downstream processor requirement.

**Acceptance criteria:** Original remains source of truth; no OCR or semantic extraction is introduced; no automatic conversion is added without a documented need.

Deferred because no concrete downstream compatibility requirement exists. No normalizer is included in the current slice.

## Phase 14 — Integration testing

**Objective:** Verify the system across real boundaries.

**Scope:** API, PostgreSQL, storage adapter, RabbitMQ, auth test doubles/emulator strategy, transaction failures, duplicate/retry scenarios, and ownership isolation.

**Deliverables:** Repeatable integration suite and fixture documents.

**Dependencies:** Phases 9–11.

**Acceptance criteria:** CI or documented local execution proves the end-to-end happy path and failure paths without requiring production credentials.

## Phase 15 — Error handling and recovery

**Objective:** Make failures diagnosable and recoverable.

**Scope:** Consistent error schema, correlation IDs, structured logs, orphan detection/reconciliation, safe retry commands, and metrics/alerts appropriate to the deployment.

**Deliverables:** Error-handling policy, recovery runbook, and tests.

**Dependencies:** Phases 10–14.

**Acceptance criteria:** Validation, storage, database, broker, and downstream failures have explicit behavior; operators can identify and safely recover incomplete work.

## Phase 16 — Documentation and release readiness

**Objective:** Make the ingestion subsystem usable and maintainable.

**Scope:** API contract, architecture decisions, configuration reference, migration/deployment instructions, supported formats/limits, security notes, and Document Understanding boundary.

**Deliverables:** Maintained project documentation and release checklist.

**Dependencies:** All preceding phases.

**Acceptance criteria:** A new developer can run the service and tests; an API consumer can perform authenticated single upload; operators understand storage, queue, retries, and recovery; future format additions have a documented extension path.
