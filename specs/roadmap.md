# Implementation Roadmap

The roadmap uses small vertical slices. Each phase should leave the repository runnable and testable. Do not begin downstream intelligence features until the source artifact, lifecycle state, and canonical object contracts are stable.

## Phase 0 — Repository and decision record

Create the package layout, settings module, Firebase project/bucket configuration contract, dependency constraints, lint/test commands, and this specification set as the review baseline.

Exit criteria: the application starts locally, configuration validation is covered, and the architecture boundaries are represented by empty interfaces/modules.

## Phase 1 — Domain contracts

Define Pydantic contracts for supported formats, canonical `Document Object`, lifecycle statuses, stable error codes, processing jobs, and normalization artifacts. Add unit tests for serialization, required fields, and invalid states.

Exit criteria: contracts can be imported without infrastructure and have compatibility tests.

## Phase 2 — Database registration model

Add SQLAlchemy models and Alembic migration for documents, processing attempts, normalization-artifact references, and verified Firebase actor identity. Add repository methods for registration, state transitions, ownership checks, and idempotency lookup.

Exit criteria: migrations run on PostgreSQL; transaction and uniqueness tests pass.

## Phase 3 — Object-storage adapter

Implement a streaming Cloud Storage for Firebase adapter that writes immutable source artifacts under a controlled document path, computes SHA-256, returns size and `gs://` URI, and supports safe object-existence/metadata checks.

Exit criteria: adapter integration tests prove successful upload, hash correctness, bounded behavior, and controlled cleanup/reconciliation signals.

## Phase 4 — Validation service

Implement filename/media-type/size validation plus file-signature checks for PDF, PNG, JPEG, DOCX, and XLSX. Define rejection codes and configurable limits. Do not parse full content in the API request.

Exit criteria: valid fixtures are accepted; mismatches, oversized files, unsupported types, and malformed signatures are rejected deterministically.

## Phase 5 — Ingestion API

Add Firebase ID-token verification middleware/dependency and expose the upload/import endpoint with streaming intake, verified actor metadata, request correlation, idempotency key handling, and the registration workflow. Return a document ID and processing status without waiting for normalization. Do not accept actor identity from request payloads.

Exit criteria: an accepted upload creates one database registration and one immutable source artifact; duplicate idempotent requests do not create duplicate logical documents.

## Phase 6 — Job publication and delivery

Add RabbitMQ topology, job schema, publisher, consumer acknowledgement behavior, retry policy, dead-letter handling, and a transactional-outbox decision/implementation if required by deployment reliability.

Exit criteria: a registered document produces a durable job; transient failures retry; poison messages are isolated; duplicate jobs are safe.

## Phase 7 — Worker skeleton and lifecycle

Implement worker startup, graceful shutdown, attempt recording, timeouts, status transitions, structured errors, and a no-op/test normalization path.

Exit criteria: jobs move through queued → processing → normalized or failed, with attempts and correlation data retained after restart.

## Phase 8 — PDF and image normalization

Implement PyMuPDF and Pillow adapters for metadata, page/image dimensions, basic extracted text where available, and normalized structural output. Add encrypted, malformed, oversized, and decompression-bomb fixtures.

Exit criteria: PDF, scanned PDF, PNG, and JPEG produce versioned normalization artifacts without changing the original source record.

## Phase 9 — DOCX and XLSX normalization

Implement python-docx and openpyxl adapters for paragraphs, tables, worksheets, bounded cell data, and document properties. Explicitly record unsupported features and limits.

Exit criteria: representative DOCX/XLSX fixtures produce deterministic artifacts, and resource-limit failures become controlled processing failures.

## Phase 10 — Canonical object assembly

Build the assembler that combines registration metadata and normalization results into the canonical `Document Object`. Version the normalization contract and test backward-compatible serialization.

Exit criteria: every successful processing path returns the object with source hash, storage URI, metadata, status, and truthful structural counts.

## Phase 11 — Reconciliation and observability

Add orphan detection for Cloud Storage/PostgreSQL mismatches, retry/reprocess commands, metrics, traces, dashboards, and alert thresholds. Add audit-safe logs, redact content-bearing values and tokens, and record Firebase UID correlation without recording raw ID tokens.

Exit criteria: operators can identify stuck jobs, reconcile partial writes, reprocess a failed attempt, and explain each document's processing history.

## Phase 12 — Hardening and release gate

Run contract, integration, load, dependency, security, and failure-injection tests. Review Firebase Auth token-revocation behavior, Storage Rules/server access boundaries, limits, retention/deletion policy, access-control integration points, and deployment runbooks.

Exit criteria: supported-format acceptance criteria are met, recovery behavior is documented, and a release can be promoted without manual database or object-storage surgery.

## Cross-phase rules

- Every phase adds tests before calling the slice complete.
- Fixtures must include benign valid files and adversarial malformed files.
- Public contracts and lifecycle transitions require review before breaking changes.
- Performance claims must be measured with representative legal-document sizes.
- OCR, semantic extraction, and user-facing search remain separate roadmap work unless explicitly brought into scope.
