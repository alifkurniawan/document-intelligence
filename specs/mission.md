# Mission: Document Ingestion and Normalization

## Purpose

Establish a reliable backend boundary that accepts external legal and Shariah documents, preserves the received artifact as the immutable source of truth, validates and registers it, and produces a canonical `Document Object` for downstream document-intelligence processing.

This subsystem optimizes for provenance, repeatability, safe failure, and explicit processing state. It must never make the normalized representation the replacement for the original artifact.

## Scope

The initial subsystem includes:

- upload/import of PDF, scanned PDF, PNG, JPEG, DOCX, and XLSX files;
- authentication of protected API requests with Firebase Authentication ID tokens;
- request-level validation of filename, media type, size, and supported format;
- streaming transfer to Cloud Storage for Firebase;
- SHA-256 content hashing and artifact identity;
- document registration and lifecycle state in PostgreSQL;
- asynchronous processing-job creation and delivery;
- format-specific normalization into a versioned normalization artifact;
- construction of the canonical `Document Object`;
- idempotency, retry, observability, and failure recording sufficient for safe reprocessing.

The subsystem does not initially include OCR quality optimization, legal clause extraction, semantic search, document editing, human review workflows, fine-grained authorization policy design, or a user interface. Those capabilities consume the canonical object and are downstream concerns. Authentication and the minimum ownership check for ingestion are in scope; the API must reject unauthenticated requests and derive the actor from the verified Firebase UID.

## Architectural flow

```text
External input
  -> Firebase Authentication ID token verification
  -> upload/import endpoint
  -> validation
  -> original artifact persisted in Cloud Storage for Firebase
  -> document registered
  -> processing job queued
  -> normalization worker
  -> normalization artifact persisted
  -> canonical Document Object
```

Registration and original-artifact persistence are treated as one business operation even though Cloud Storage for Firebase and the database are separate systems. The implementation must use an explicit pending/committed state and reconciliation path; it must not claim successful ingestion when only one side succeeded.

## Source-of-truth rules

1. The original bytes are immutable after successful ingestion.
2. The stored SHA-256 hash is calculated from the received bytes and is independently verifiable.
3. Normalization is derived data. It is versioned, replaceable, and never used to reconstruct the source artifact.
4. Every derived record references the document identity, original hash, normalizer version, and processing attempt.
5. A retry may create a new processing attempt, but must not create a second logical document for the same idempotent request.

## Canonical Document Object

The first contract is intentionally small and stable:

```json
{
  "document_id": "uuid",
  "original_file": {
    "filename": "contract.pdf",
    "mime_type": "application/pdf",
    "size": 123456,
    "hash": "sha256:...",
    "pages": 12,
    "storage_uri": "gs://firebase-storage-bucket/documents/uuid/source/contract.pdf"
  },
  "metadata": {
    "uploaded_at": "2026-01-01T00:00:00Z",
    "uploaded_by": "firebase-uid"
  },
  "processing_status": "queued"
}
```

`pages` is a best-effort structural count. For XLSX it may represent worksheets or remain null until a contract decision is made; it must not be fabricated. MIME type is validated but format detection should also inspect file signatures where practical.

The status vocabulary begins with `queued`, `processing`, `normalized`, `failed`, and `rejected`. State transitions are monotonic per attempt, auditable, and controlled by the service rather than client input.

## Quality and safety invariants

- Never load an unbounded upload into memory.
- Enforce configurable maximum size and resource budgets before expensive parsing.
- Treat malformed, encrypted, password-protected, or parser-hostile files as controlled failures.
- Isolate parsing from the API process and apply worker timeouts.
- Do not log document contents, credentials, or presigned URLs.
- Require a valid Firebase ID token for protected ingestion endpoints; use its verified `uid` as `uploaded_by` and reject client-supplied actor identity.
- Keep Firebase service-account credentials and bucket configuration outside source control.
- Keep enough metadata to reproduce why a file was accepted, rejected, or failed.
- Return stable error codes and correlation identifiers.
- Make all external integrations replaceable behind ports/interfaces.

## Definition of done for this constitution

An implementation is foundationally complete when a supported file can be uploaded, durably registered, processed asynchronously, and represented by the canonical object; when invalid input is rejected deterministically; when worker failure is retryable and observable; and when the original artifact and its hash remain independently verifiable.
