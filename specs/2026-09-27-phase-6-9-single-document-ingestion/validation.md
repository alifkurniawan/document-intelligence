# Phases 6–9 Validation and Merge Criteria

## Automated checks

1. Ruff formatting and linting pass.
2. The full pytest suite passes.
3. Clean migrations apply and relevant PostgreSQL integration tests pass.
4. Firebase, storage, and external-service behavior is covered by deterministic fakes/emulators or documented integration configuration.

## Storage and validation behavior

1. Valid supported PDF, scanned PDF, configured images, DOCX, and XLSX inputs pass.
2. Unsupported extensions/MIME types, oversize inputs, unsafe filenames, unreadable streams, corrupt files, and content/type mismatches produce deterministic errors.
3. Uploads stream within configured limits and calculate verifiable SHA-256 and byte size.
4. Stored originals can be read back and match the submitted bytes and metadata.
5. Original storage paths are document-scoped and immutable; retries never silently overwrite an existing object.

## Registration and API behavior

1. An authenticated upload creates exactly one owner-scoped document, one original artifact, and one queued processing job.
2. No accepted document exists without a resolvable original and complete original metadata.
3. Storage/database failure paths do not leave an API response claiming successful acceptance; cleanup or recovery behavior is tested.
4. Unauthenticated requests, invalid tokens, other-owner access, validation failures, conflicts, and infrastructure failures map to documented status codes and error schemas.
5. A successful response contains `document_id`, original metadata, uploader/time metadata, and queued status, and returns without downstream processing.

## Boundary and security review

1. API routes call application services and do not contain storage, SQLAlchemy, or provider orchestration.
2. Domain/application contracts do not expose Firebase, SQLAlchemy, or storage SDK objects.
3. PostgreSQL stores metadata/references only; binary bytes are absent from database records, API responses, and future job payloads.
4. Credentials and limits are configuration-driven; no secrets or connection strings are committed.
5. The implementation contains no OCR, semantic extraction, classification, legal analysis, or implicit normalization.

## Merge decision

Merge is allowed when the confirmed requirements, automated tests, storage read-back/hash checks, transaction/recovery checks, API contract tests, and architecture/security review pass with no unrelated changes.
