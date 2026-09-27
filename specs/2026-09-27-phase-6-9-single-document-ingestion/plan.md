# Phases 6–9 Implementation Plan — Single-Document Ingestion

## Task group 1 — Define the cross-phase contracts

1. Confirm the artifact-storage, file-validation, registration, authentication, and upload-response contracts.
2. Map the existing Phase 4 domain types and Phase 5 repositories to the registration workflow.
3. Define stable application errors and their API status-code mapping without exposing provider exceptions.
4. Record the transaction/compensation boundary between external storage and PostgreSQL metadata.

## Task group 2 — Implement artifact storage

1. Add an async artifact-storage port for streaming writes, metadata inspection, and immutable references.
2. Implement a Firebase Storage adapter using document-scoped, non-overwriting original paths.
3. Implement a local/test adapter with equivalent immutability and read-back behavior.
4. Stream input while calculating SHA-256 and byte size; verify the stored object before returning its reference.
5. Ensure retries cannot silently replace an existing original artifact.

## Task group 3 — Implement file validation

1. Add safe filename normalization and configured extension/MIME/size policy.
2. Add readability and integrity checks for PDF, images, DOCX, and XLSX using bounded reads.
3. Detect extension/MIME/content mismatches and return deterministic validation errors.
4. Keep validation technical only; do not OCR, classify, extract semantics, or normalize without a concrete requirement.
5. Test supported, unsupported, oversize, unreadable, corrupt, and mismatched inputs.

## Task group 4 — Implement document registration

1. Add an application service that validates the input, stores the original, and persists document/artifact/job metadata.
2. Enforce authenticated ownership and complete original-artifact metadata.
3. Coordinate storage and repository transactions so no accepted record points to a missing or uncommitted original.
4. Create a queued processing job after the document and original artifact are durably resolvable.
5. Define safe cleanup/retry behavior for failures between storage and database commits.

## Task group 5 — Expose the single-document upload API

1. Add Firebase email-auth token verification behind an authentication port and map the result to the owner identity.
2. Add the multipart upload route, request limits, response schemas, and OpenAPI examples.
3. Invoke the registration service from the handler; keep business orchestration out of FastAPI routes.
4. Return `document_id`, original metadata, uploader/time metadata, and queued status without waiting for downstream processing.
5. Enforce ownership isolation and deterministic HTTP errors for authentication, validation, conflict, and infrastructure failures.

## Task group 6 — Verify and prepare for handoff

1. Add unit tests for contracts, validation, storage immutability, registration failures, and error mapping.
2. Add API/integration tests for authenticated upload, ownership isolation, rollback/cleanup, and queued response behavior.
3. Verify configuration, migrations, supported-format documentation, and absence of binary data in PostgreSQL or response/job payloads.
4. Run formatting, linting, the full test suite, and the relevant PostgreSQL/storage integration tests.
5. Resolve the open decisions in `requirements.md` before implementation is considered complete.
