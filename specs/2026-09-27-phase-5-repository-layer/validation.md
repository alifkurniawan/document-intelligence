# Phase 5 Validation and Merge Criteria

## Automated checks

1. Ruff formatting and linting pass.
2. The full pytest suite passes.
3. PostgreSQL integration tests pass against an isolated database.
4. Migrations apply cleanly from an empty database.

## Repository behavior

1. Documents, artifacts, and jobs can be created and retrieved through stable repository contracts.
2. Owner-scoped queries return only authorized owner records.
3. Document IDs, artifact IDs, job IDs, foreign keys, and required metadata are enforced.
4. Duplicate identities and invalid relationships produce deterministic conflict/errors.
5. A coordinated metadata write commits atomically or rolls back entirely.
6. Original artifacts cannot be overwritten through repository operations.
7. PostgreSQL contains metadata and storage references only; no document bytes are persisted.

## Architecture and security review

1. Domain/application contracts do not expose SQLAlchemy models or sessions.
2. Repository implementations use the Phase 3 session boundary.
3. No RabbitMQ message publishing or external-provider behavior is pulled into this phase.
4. Migrations contain no secrets, destructive unapproved data operations, or unrelated schema.

## Merge decision

Merge is allowed when the confirmed requirements, migrations, unit/integration tests, transaction checks, and architecture/security review pass with no unrelated changes.
