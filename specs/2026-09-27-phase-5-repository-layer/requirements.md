# Phase 5 Feature Specification — Repository Layer

## Context

Phase 5 persists the provider-neutral concepts from Phase 4 using the database infrastructure from Phase 3. The [mission](../mission.md) requires durable document, immutable original-artifact, owner, and processing-job metadata while keeping binary content outside PostgreSQL. The [tech stack](../tech-stack.md) requires repository contracts to hide SQLAlchemy and transaction behavior from the domain/application contracts.

## Scope

The implementation must provide:

1. Repository contracts for documents, artifacts, and processing jobs.
2. SQLAlchemy implementations and ORM mappings.
3. Constraints and indexes for identity, ownership, relationships, state, and lookup paths.
4. Transaction boundaries that can atomically persist document/artifact/job metadata.
5. Alembic migrations and PostgreSQL integration tests.

## Proposed persistence model

* `documents`: document ID, owner ID, lifecycle status, timestamps, and any confirmed document-level metadata.
* `artifacts`: artifact ID, document ID, role, original filename, MIME type, byte size, SHA-256, storage reference, upload time, and immutability/provenance fields.
* `processing_jobs`: job ID, document ID, state, retry metadata, error metadata, and timestamps.
* Foreign keys and unique constraints prevent orphaned artifacts/jobs and duplicate logical identities.
* Indexes support owner-scoped document queries and document/job/artifact lookups.

## Confirmed decisions

* Use async SQLAlchemy ORM models only inside infrastructure and map to domain types at the repository boundary.
* Keep original artifact bytes and RabbitMQ payloads outside PostgreSQL.
* Create document and original artifact metadata in one transaction through the repository layer; defer initial queued-job creation to the registration application service.
* Do not publish RabbitMQ messages in this phase; message delivery is Phase 10 and requires a separately documented coordination strategy.
* Use application-generated UUIDs, database constraints for uniqueness and referential integrity, and application-level domain checks for ownership and transitions.
* Persist exactly one original artifact per document, with zero or more derivative artifacts.
* Exclude soft deletion from the initial schema.

## Constraints and non-goals

* Do not implement upload APIs, Firebase authorization, object storage, RabbitMQ publishing, file validation, normalization, OCR, or Document Understanding.
* Do not allow repository queries to return another owner’s documents through an unscoped method used by application code.
* Do not overwrite original artifact metadata or storage references.
* Do not add an outbox table unless the confirmed transaction/message coordination design requires it at this phase; record it as a Phase 10 decision otherwise.

## Future compatibility

Phase 8 registration will orchestrate validation, storage, repository writes, and job creation. Phase 10 will add broker publication without placing binary data in messages. Repository contracts should remain stable as Firebase, storage, and RabbitMQ adapters are added.
