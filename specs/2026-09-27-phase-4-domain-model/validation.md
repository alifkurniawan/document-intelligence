# Phase 4 Validation and Merge Criteria

## Automated checks

1. Ruff formatting and linting pass.
2. The full pytest suite passes.
3. Domain tests run without PostgreSQL, SQLAlchemy, Firebase, RabbitMQ, storage, or network access.

## Domain behavior

1. Valid documents, artifacts, owners, and jobs can be constructed.
2. Application-generated UUIDs, owner identity, original metadata, hash, size, and storage reference are enforced.
3. Exactly one original artifact is allowed per document; its provenance cannot be overwritten or silently replaced.
4. Valid lifecycle transitions succeed.
5. Invalid transitions raise deterministic domain errors.
6. Ownership checks prevent one account from operating on another account’s document.
7. Jobs cannot be queued without a resolvable original-artifact reference.

## Architecture and boundary review

1. Domain modules contain no SQLAlchemy, FastAPI, Firebase, RabbitMQ, or storage imports.
2. No binary content is represented as a domain field or message payload.
3. No Document Understanding behavior is present.
4. Domain errors are provider-neutral and suitable for later application/API mapping.

## Merge decision

Merge is allowed when the confirmed requirements, pure unit tests, and architecture/boundary review pass with no unrelated behavior.
