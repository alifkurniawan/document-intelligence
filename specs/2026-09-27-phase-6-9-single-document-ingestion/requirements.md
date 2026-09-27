# Phases 6–9 Feature Specification — Single-Document Ingestion

## Context

Phases 6–9 form the first end-to-end ingestion slice: preserve an uploaded original, reject invalid input, register durable metadata, and expose the authenticated single-document upload API. This specification follows the [mission](../mission.md), [roadmap](../roadmap.md), and [tech stack](../tech-stack.md). The original artifact remains the source of truth; PostgreSQL stores metadata and storage references only; downstream understanding is out of scope.

## Scope

The implementation must provide:

1. A replaceable artifact-storage port with Firebase Storage and local/test adapters.
2. Immutable, document-scoped original paths with streaming upload and SHA-256/size verification.
3. Extension, MIME, size, filename, readability, integrity, and conservative format checks for PDF, scanned PDF, JPEG, PNG, other configured image formats, DOCX, and XLSX.
4. A registration service that creates the owner-scoped document, original artifact, and queued processing job using Phase 5 repositories.
5. Firebase email-auth token verification behind an authentication boundary.
6. A multipart upload endpoint with typed response/error schemas and OpenAPI examples.

## Confirmed decisions

* The feature is planned as one branch/spec for phases 6–9 because each phase is a dependency of the next.
* Phases 6–9 remain one combined, independently reviewable feature slice and branch.
* Original bytes are stored outside PostgreSQL and are never included in RabbitMQ messages or API responses.
* Originals are immutable and must not be overwritten by retries, normalization, or processing.
* Local development and CI use a filesystem-backed storage adapter for integration tests and an in-memory adapter for unit tests.
* If storage succeeds but database registration fails, best-effort deletion is sufficient; durable orphan reconciliation is deferred.
* Client-provided MIME values are hints. The implementation derives the authoritative type from content and rejects mismatches.
* Validation is technical only. No OCR, semantic extraction, classification, legal analysis, or automatic format conversion is included.
* The upload response returns after durable registration and queued-job creation; it does not wait for downstream processing.
* Provider-specific Firebase and storage behavior stays behind application-facing ports.
* Configuration, credentials, supported formats, and limits come from environment-backed settings.

## Proposed workflow

1. Verify the Firebase token and establish the authenticated owner.
2. Read/stream the multipart input through filename/type/size/integrity validation.
3. Allocate a document identity and upload the original to a unique document-scoped path without overwrite.
4. Verify stored bytes and persist document, original-artifact, and queued-job metadata through the repository transaction boundary.
5. Return document information and queued status.

If metadata persistence fails after storage succeeds, the implementation must perform safe cleanup when possible or record a recoverable orphan; it must never return an accepted document that cannot resolve its original.

## Required metadata and behavior

An accepted original records filename, MIME type, byte size, SHA-256, storage reference, upload timestamp, authenticated uploader, document ID, and queued job/status metadata. Duplicate, malformed, unsupported, oversize, unreadable, corrupt, and extension/MIME-mismatched inputs produce stable errors. Authorization is account ownership.

## Resolved feature decisions

The four planning decisions are confirmed: phases 6–9 use one combined feature branch/spec; filesystem storage is used for integration tests and in-memory storage for unit tests; storage cleanup after registration failure is best-effort; and content-derived MIME detection is authoritative, with mismatches rejected.

## Non-goals

Do not implement RabbitMQ publishing, downstream consumers, OCR, Document Understanding, semantic metadata, batch/import workflows, broad normalization, soft deletion, or a separate document-download API unless a confirmed dependency requires it.
