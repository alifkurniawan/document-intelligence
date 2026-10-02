# Roadmap

The roadmap is intentionally incremental. Each phase should be independently reviewable and testable. The single-document workflow is the MVP core; batch/import is planned as an adapter that reuses it.

## Phase 1 — Project foundation — Complete

**Objective:** Establish a runnable, maintainable Python service.

**Scope:** Layered application package layout (`api`, `core`, `models`, `services`, `repositories`, `storage`, `workers`, and `schemas`), FastAPI entry point, dependency management, health endpoint, baseline logging, test layout, and CI-quality commands.

**Deliverables:** Minimal service, `pyproject.toml` configuration, test harness, README development commands.

**Dependencies:** None.

**Acceptance criteria:** Service starts from documented commands, health check works, and an empty baseline test suite runs.

## Phase 2 — Configuration — Complete

**Objective:** Centralize environment-driven settings.

**Scope:** Typed settings, `.env.example`, environment validation, limits, allowlists, Firebase, PostgreSQL, RabbitMQ, storage, and stable JWT-signing-key settings.

**Deliverables:** `app/core/config.py`, `.env.example`, and configuration documentation.

**Dependencies:** Phase 1.

**Acceptance criteria:** No secrets or connection strings are hard-coded; missing required production settings fail clearly.

## Phase 3 — Database setup — Complete

**Objective:** Make metadata persistence reproducible.

**Scope:** PostgreSQL connection/session management in `app/core/database.py`, SQLAlchemy base and models in `app/models/database.py`, Alembic, and initial migration wiring.

**Deliverables:** Migration commands and database integration tests.

**Dependencies:** Phase 2.

**Acceptance criteria:** A clean database can be migrated up and application sessions can be opened and closed safely.

## Phase 4 — Domain model — Complete

**Objective:** Define provider-neutral ingestion concepts.

**Scope:** Provider-neutral Document, Artifact, ProcessingJob, OutboxMessage, authenticated-owner concepts, processing states, invariants, and shared errors in `app/models/entities.py` and `app/core/errors.py`.

**Deliverables:** Provider-neutral model entities and unit tests.

**Dependencies:** Phase 1; database vocabulary from Phase 3.

**Acceptance criteria:** Domain tests cover ownership, immutable original semantics, valid states, and invalid transitions without importing Firebase or SQLAlchemy.

## Phase 5 — Repository layer — Complete

**Objective:** Persist documents, artifacts, and jobs behind stable interfaces.

**Scope:** SQLAlchemy repository implementations in `app/repositories/document.py`, constraints, indexes, and the metadata unit-of-work transaction boundary.

**Deliverables:** Repositories and migration updates.

**Dependencies:** Phases 3–4.

**Acceptance criteria:** Metadata can be created, queried by owner/document ID, and rolled back atomically in integration tests. Services own Unit of Work execution; HTTP routes do not call repositories.

## Phase 6 — File storage abstraction — Complete (MVP)

**Objective:** Preserve original binaries outside PostgreSQL.

**Scope:** Artifact storage protocol, Firebase Storage adapter, in-memory/filesystem test adapters, immutable document-scoped paths, and hash/size verification.

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

**Scope:** `DocumentIngestionService`, ownership, metadata, original-artifact record, queued processing state, and transactional outbox record.

**Deliverables:** Service orchestration and transaction tests.

**Dependencies:** Phases 4–7.

**Acceptance criteria:** Successful registration has a unique document ID, complete original metadata, and no accepted record exists without a resolvable original.

## Phase 9 — Single-document upload API — Complete (MVP)

**Objective:** Expose the first end-to-end ingestion workflow.

**Scope:** Firebase email-auth token verification, ownership authorization, multipart upload, request/response schemas, the shared JSON response envelope, paginated document listing, status codes, and document information response.

**Deliverables:** Upload endpoint and OpenAPI examples.

**Dependencies:** Phases 2 and 8.

**Acceptance criteria:** An authenticated user can upload one supported document and receive the document information inside the shared `{data, message}` envelope, without downstream processing delay. JSON lists use the documented page envelope.

Production hardening follow-ups remain for atomic Firebase non-overwrite semantics,
Firebase SDK initialization, true streaming storage, and stronger PDF integrity checks.

## Phase 10 — RabbitMQ integration — Complete

**Objective:** Publish durable processing job references.

**Scope:** Exchange/queue topology, `app/workers/rabbitmq.py` publisher adapter, reference-only processing message contract, publisher confirms, and configuration.

**Deliverables:** RabbitMQ adapter and contract tests.

**Dependencies:** Phases 5 and 8.

**Acceptance criteria:** No binary data appears in messages; messages are traceable to a persisted job and use documented delivery settings.

Implemented with durable exchange/queue/DLQ declarations, publisher confirms, reference-only
messages, environment-backed settings, a transactional outbox, and the runnable
`app.workers.worker` outbox publisher. The downstream processing consumer remains an
external boundary.

## Phase 11 — Asynchronous processing hand-off — Complete

**Objective:** Make job state and retry behavior operationally safe.

**Scope:** Consumer-facing job contract, queued/processing/completed/failed states, acknowledgement rules, bounded retry, and dead-letter handling where needed.

**Deliverables:** Job manager behavior, state-transition tests, and runbook.

**Dependencies:** Phase 10.

**Acceptance criteria:** Upload returns before processing completion; transient failures can retry; permanent failures are visible and do not silently lose the original.

Implemented with provider-neutral processing contracts in `app/workers/contracts.py`, legal
job transitions, bounded exponential retry policy, dead-letter decisions, and a runnable
outbox hand-off worker.
Actual Document Understanding consumption remains downstream and is not part of ingestion.

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

## Phase 14 — Integration testing — Complete

**Status:** Complete for the current MVP slice. Isolated Docker Compose topology,
deterministic focused tests, owner-scoped retrieval, and recovery seams are documented.

**Objective:** Verify the system across real boundaries.

**Scope:** API, PostgreSQL, storage adapter, RabbitMQ, auth test doubles/emulator strategy, transaction failures, duplicate/retry scenarios, and ownership isolation.

**Deliverables:** Repeatable integration suite and fixture documents.

**Dependencies:** Phases 9–11.

**Acceptance criteria:** CI or documented local execution proves the end-to-end happy path and failure paths without requiring production credentials.

## Phase 15 — Error handling and recovery — Complete

**Status:** Complete for the current MVP slice. Correlation-aware global exception
handlers, a consistent error envelope, safe operational logging, conservative
reconciliation, bounded recovery contracts, metrics, and the recovery runbook are
implemented.

**Objective:** Make failures diagnosable and recoverable.

**Scope:** Consistent error schema, correlation IDs, structured logs, orphan detection/reconciliation, safe retry commands, and metrics/alerts appropriate to the deployment.

**Deliverables:** Error-handling policy, recovery runbook, and tests.

**Dependencies:** Phases 10–14.

**Acceptance criteria:** Validation, storage, database, broker, and downstream failures have explicit behavior; operators can identify and safely recover incomplete work.

## Phase 16 — Documentation and release readiness — Complete

**Objective:** Make the ingestion subsystem usable and maintainable.

**Scope:** API contract, architecture decisions, configuration reference, migration/deployment instructions, supported formats/limits, security notes, and Document Understanding boundary.

**Deliverables:** Maintained project documentation and release checklist.

**Dependencies:** All preceding phases.

**Acceptance criteria:** A new developer can run the service and tests; an API consumer can perform authenticated single upload; operators understand storage, queue, retries, and recovery; future format additions have a documented extension path.

Implemented in `README.md` and `docs/`: API contract, architecture decisions,
configuration, deployment/migration guidance, PyCharm run/debug configurations,
security notes, recovery operations, Document Understanding boundary, and release
checklist. `main.py` launches the local API while PostgreSQL and RabbitMQ run from
the integration Compose profile.

## Phase 17 — Document Understanding — Complete

**Objective:** Transform immutable original document artifacts into a structured,
machine-readable Document Representation and traceable semantic information.

**Scope:** Document inspection, processor selection by document characteristics,
content extraction, OCR when required, structure/layout and reading-order analysis,
Document Representation, provenance, version-aware processing, semantic extraction,
processing status, retry, failure reporting, and reprocessing from an existing
original artifact.

The initial processor policy uses the simplest appropriate method: text parsing for
text PDFs, OCR for scanned PDFs and images, DOCX parsing for DOCX, and spreadsheet
parsing for XLSX. OCR is a first-class capability and PaddleOCR is the preferred
initial implementation. The architecture must keep the OCR engine replaceable and
must not require OCR, VLM, or LLM processing for every document.

**Dependencies:** Phases 10–11 and the immutable original-artifact contract.

**Acceptance criteria:** A future implementation can consume a persisted original by
reference, select an appropriate processor, produce a representation containing
content and observable structure, retain practical source provenance, associate
results with applicable processor/model/prompt/logic versions and timestamps, and
retry or reprocess without a new upload. The original artifact remains immutable.

**Non-goals:** RAG, vector search, question answering, document comparison, legal
reasoning or analysis, Shariah analysis, legal risk analysis, recommendations, and
autonomous agents. Detailed representation schemas, processor contracts, and
semantic extraction taxonomies belong to a future feature specification.

Implemented with characteristic-driven processor selection, immutable original
artifact access, versioned document representations, provenance, semantic
extraction, bounded retry, failure reporting, and reprocessing from an existing
original artifact. Supported PDF, image/OCR, DOCX, and XLSX paths remain behind
replaceable processing boundaries.

## Phase 18 — Auditable document soft deletion — Complete

**Objective:** Let an authenticated owner remove a document from their ordinary list while retaining its record and provenance.

**Scope:** Owner-scoped `DELETE /documents/{document_id}`, persisted deletion timestamp and actor, list filtering, owner-visible audit fields, and an additive database migration.

**Deliverables:** Soft-delete metadata, repository and API behavior, and API/mission documentation.

**Dependencies:** Phases 3, 5, and 9.

**Acceptance criteria:** A successful delete hides the document from the owner's list, retains the original and metadata, records the first authenticated deleting user and timestamp, and never changes another owner's record.

Implemented with migration `0005_document_soft_delete`, idempotent owner-scoped deletion, and deletion actor/timestamp in detail and delete responses.

## Phase 19 — Unified API responses and pagination — Complete

**Objective:** Give clients one JSON response contract and bounded, query-backed document listing.

**Scope:** Generic `{data, message}` success/error envelopes, paginated list payloads with `current_page`, `total_data`, and `total_page`, and envelope-compatible original-document retrieval.

**Deliverables:** Shared schemas, global error-envelope mapping, SQL-backed list count/offset/limit, and API documentation.

**Dependencies:** Phases 9, 15, and 18.

**Acceptance criteria:** Every JSON route uses the shared envelope; the document list is owner-scoped, soft-delete filtered, and paginated in PostgreSQL; page size is bounded. Original bytes are represented as Base64 in the authorized JSON download response.

Implemented in `app/schemas/responses.py`, document routes and repository pagination, and `app/api/exception_handlers.py`.

## Phase 20 — Service-layer Unit of Work boundary — Complete

**Objective:** Keep HTTP endpoints focused on request/response handling.

**Scope:** Move document list, detail, soft-delete, and original-read repository workflows into an application service that owns Unit of Work execution.

**Deliverables:** `DocumentManagementService` and API dependency wiring.

**Dependencies:** Phases 5, 9, and 18.

**Acceptance criteria:** API route handlers do not open Unit of Work contexts or call repositories; application services coordinate repositories and transactions.

Implemented in `app/services/document_management.py`; `app/api/routes/documents.py` delegates those operations to the service.
