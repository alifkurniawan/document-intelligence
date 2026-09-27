# Phase 3 Validation and Merge Criteria

## Automated checks

1. Ruff formatting and linting pass.
2. The full pytest suite passes.
3. Database integration tests pass against an isolated PostgreSQL database.
4. No test requires production Firebase, RabbitMQ, storage, or credentials.

## Database behavior

1. A clean PostgreSQL database can run the documented Alembic upgrade command successfully and contains the confirmed Phase 4/5 tables.
2. The configured SQLAlchemy engine and session can connect and close safely.
3. A committed transaction persists a test record or schema-level change as appropriate.
4. A failed transaction rolls back and does not leak a session or connection.
5. Alembic uses the configured URL without hard-coded credentials.
6. Importing application modules does not open a database connection.

## Architecture and security review

1. SQLAlchemy and Alembic stay in infrastructure modules.
2. `/health` remains independent of PostgreSQL.
3. No document binary data or secrets are added to the database or repository.
4. The diff contains no business workflow or Document Understanding behavior.

## Merge decision

Merge is allowed when the confirmed requirements, automated checks, migration checks, and architecture/security review all pass. Any unresolved choice must be recorded as a follow-up.
