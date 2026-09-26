# Phase 1 — Domain contracts requirements

## Scope

This slice establishes importable, infrastructure-independent Pydantic 2.x contracts for the ingestion and normalization subsystem. It covers supported formats, the canonical `Document Object`, lifecycle statuses, stable error codes, processing jobs, and normalization artifacts.

It does not implement persistence, Firebase verification, object storage, RabbitMQ, parsing, OCR, API endpoints, or worker behavior.

## Guidance

- Preserve the original artifact as the immutable source of truth.
- Keep normalization derived, versioned, replaceable, and linked to the original hash.
- Derive actor identity from verified Firebase context in later phases; domain contracts must not trust a client-supplied actor identity.
- Keep contracts separate from SQLAlchemy persistence models and adapter-specific parser output.
- Enforce bounded, explicit values and reject impossible lifecycle states.
- Use stable names and serialized forms so later phases can depend on these contracts without breaking changes.

## Baseline decisions

- Python 3.12+ and Pydantic 2.x, following `specs/tech-stack.md`.
- Supported source formats: PDF, scanned PDF, PNG, JPEG, DOCX, and XLSX.
- Canonical status vocabulary begins with `queued`, `processing`, `normalized`, `failed`, and `rejected`.
- A source hash is represented as a SHA-256 value with an explicit `sha256:` prefix.
- Processing jobs carry document identity, source identity, attempt identity, and correlation information, but not document bytes.
- Normalization artifacts carry the source hash, normalizer version, processing attempt, and versioned structural output.
- UUIDs are validated strictly, and all timestamps are required to be timezone-aware.
- The canonical `Document Object` leaves `pages` as `null` for XLSX rather than fabricating a page count.
- A failed document may return to `queued` after two attempts, subject to the implementation's explicit retry guard and audit trail.
- A normalized document may be reprocessed only after explicit user approval; that approval must be represented in the application workflow rather than inferred from a client status value.
- Normalization output is an opaque, versioned payload at this phase; format-specific structure is owned by later normalizer contracts.
- Error codes use lowercase, namespaced, machine-readable identifiers with a stable semantic prefix and a separate human-readable message. Recommended namespaces are `validation.*`, `storage.*`, `processing.*`, `auth.*`, and `conflict.*`.

### Error-code convention

Codes are stable API/domain identifiers and must not contain dynamic values, parser exception text, credentials, or document content. The payload should expose the code, a safe message, and a correlation ID; logs may include the document/attempt identifiers separately.

Initial examples:

- `validation.unsupported_format`
- `validation.media_type_mismatch`
- `validation.signature_mismatch`
- `validation.size_limit_exceeded`
- `auth.invalid_identity`
- `storage.artifact_missing`
- `storage.artifact_hash_mismatch`
- `processing.parse_failed`
- `processing.timeout`
- `processing.retry_exhausted`
- `conflict.idempotency_mismatch`
- `conflict.invalid_status_transition`

## Resolved feature decisions

The feature decisions above resolve the Phase 1 open questions. The implementation must still define the exact attempt-count boundary and approval representation in its contract tests and review notes.
