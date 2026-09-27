# Phase 4 Implementation Plan — Domain Model

## Task group 1 — Define provider-neutral domain types

1. Define application-generated UUID identifiers and authenticated-owner representation.
2. Define `Document`, `Artifact`, and `ProcessingJob` concepts with separate document/job status enums and without importing SQLAlchemy, Firebase, FastAPI, or RabbitMQ.
3. Define timestamps, hashes, storage references, filenames, MIME types, and sizes with appropriate invariants.
4. Enforce exactly one original artifact per document while allowing future technical derivatives.

## Task group 2 — Define lifecycle states and transitions

1. Model the agreed document/job states from the ingestion lifecycle.
2. Define valid transitions and reject invalid transitions with domain errors.
3. Preserve the invariant that a job cannot be queued for an unresolved original artifact.
4. Define retry/failure semantics without implementing RabbitMQ behavior; defer technical metadata such as page count.

## Task group 3 — Enforce ownership and immutability invariants

1. Require a stable authenticated owner for accepted documents.
2. Prevent replacement or mutation of original-artifact identity and provenance fields.
3. Make ownership checks explicit and provider-neutral.
4. Define domain errors that application/API layers can map later without leaking infrastructure exceptions.

## Task group 4 — Add domain unit tests and documentation

1. Test valid construction for documents, original artifacts, and jobs.
2. Test ownership isolation, immutable originals, valid transitions, and invalid transitions.
3. Test domain modules import without database or provider dependencies.
4. Document any state or identity decisions that repositories must preserve.

## Task group 5 — Verify and prepare for handoff

1. Run formatting, lint, and the full unit-test suite.
2. Review the model against the mission boundary and supported ingestion lifecycle.
3. Confirm no OCR, semantic extraction, or provider-specific behavior entered the domain.
4. Confirm every criterion in `validation.md` before merge.
