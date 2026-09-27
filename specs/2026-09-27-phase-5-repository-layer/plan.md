# Phase 5 Implementation Plan — Repository Layer

## Task group 1 — Define repository contracts

1. Define async repository interfaces for documents, artifacts, and processing jobs around domain types.
2. Define owner/document lookup methods and not-found/conflict behavior.
3. Define async transaction/unit-of-work boundaries for document and artifact metadata; leave initial job creation to the registration service.
4. Keep contracts independent of SQLAlchemy sessions and provider-specific exceptions.

## Task group 2 — Map domain types to SQLAlchemy models

1. Add async-compatible ORM models and relationships for documents, artifacts, and jobs.
2. Enforce uniqueness, foreign keys, immutability-related constraints, indexes, and required metadata in the schema.
3. Store metadata and storage references only; never store binary document contents.
4. Keep mappings explicit and prevent ORM objects from crossing the application/domain boundary.

## Task group 3 — Implement repository behavior

1. Implement create, retrieve, and owner-scoped query operations.
2. Implement original-artifact and job association rules.
3. Implement transaction commit/rollback behavior for coordinated metadata writes.
4. Translate database integrity/not-found failures into stable repository/application errors.

## Task group 4 — Add migrations and integration tests

1. Add a reviewable Alembic migration for the confirmed tables, constraints, and indexes.
2. Test async metadata creation and retrieval by owner/document ID against the Docker Compose PostgreSQL service.
3. Test duplicate/conflict behavior, ownership isolation, and rollback atomicity.
4. Test that stored records contain references and metadata, not binary contents.

## Task group 5 — Verify and prepare for handoff

1. Run formatting, lint, unit tests, and PostgreSQL integration tests.
2. Run migrations from a clean database and inspect the generated schema.
3. Review transaction boundaries against the original-artifact and queued-job invariants.
4. Confirm every criterion in `validation.md` before merge.
