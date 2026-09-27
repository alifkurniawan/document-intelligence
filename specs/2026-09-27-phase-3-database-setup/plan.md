# Phase 3 Implementation Plan — Database Setup

## Task group 1 — Establish database configuration and engine boundaries

1. Confirm the PostgreSQL URL and environment configuration contract from Phase 2, including async driver settings where needed.
2. Add a database infrastructure module that creates the SQLAlchemy engine without opening a connection at import time.
3. Define async engine pool, echo, and lifecycle settings appropriate for development, test, and production.
4. Keep database infrastructure independent from domain entities and API handlers.

## Task group 2 — Add session and declarative-base infrastructure

1. Create the SQLAlchemy declarative base used by future metadata models.
2. Provide a session factory and an application-safe session lifecycle/dependency boundary.
3. Ensure async sessions are committed, rolled back, and closed deterministically.
4. Keep ORM metadata separate from provider-neutral domain types planned for Phase 4.

## Task group 3 — Wire Alembic

1. Add Alembic configuration using the configured database URL without committing credentials.
2. Add the initial migration wiring and metadata import path.
3. Make upgrade and downgrade commands work against a clean PostgreSQL database.
4. Include the confirmed Phase 4/5 document, artifact, and processing-job tables in the initial migration.

## Task group 4 — Add database integration tests and documentation

1. Document local PostgreSQL startup and migration commands.
2. Test async engine/session construction with isolated configuration.
3. Test an async session can open, commit, roll back, and close against the Docker Compose PostgreSQL service.
4. Ensure tests do not require production credentials or Firebase/RabbitMQ.

## Task group 5 — Verify and prepare for handoff

1. Run formatting, lint, unit tests, and database integration tests.
2. Run migrations up and down against a clean test database.
3. Review the diff for secrets, import-time connections, and unrelated schema.
4. Confirm every criterion in `validation.md` before merge.
