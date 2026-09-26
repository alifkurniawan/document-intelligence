# Tech Stack

## Baseline

The initial implementation uses Python 3.14, FastAPI, PostgreSQL, SQLAlchemy, Alembic, RabbitMQ, Firebase Authentication, and Firebase Storage. These are infrastructure choices behind application interfaces where replacement is practical; they are not domain concepts.

## Python 3.14

**Why:** The project standardizes on the current target runtime and its typing, async, and maintenance improvements.

**Owns:** Application runtime, domain/application code, validation orchestration, adapters, and tests.

**Must not own:** Persistence semantics, object-storage semantics, message-broker guarantees, or authentication policy by implicit convention.

**Constraints:** Pin and test supported dependency versions. Keep I/O boundaries explicit and avoid blocking work in async request handlers.

## FastAPI

**Why:** Provides typed HTTP APIs, dependency injection, OpenAPI documentation, and an appropriate async web runtime.

**Owns:** HTTP routing, request/response schemas, authentication context integration, and HTTP status mapping.

**Must not own:** Ingestion business rules, transaction orchestration, direct SQL, object-storage implementation, or message publishing logic.

**Constraints:** API handlers call application services. Schemas are not used as domain entities by accident.

## PostgreSQL and SQLAlchemy

**Why:** PostgreSQL provides durable transactional metadata storage; SQLAlchemy provides a maintainable ORM and database abstraction.

**Owns:** Documents, artifacts, jobs, ownership metadata, state, hashes, storage references, timestamps, and indexes; SQLAlchemy maps these records and manages database access.

**Must not own:** Binary document contents, file validation policy, object storage, or RabbitMQ delivery.

**Constraints:** Store metadata only, use transactions for document/artifact/job coordination, enforce uniqueness and state invariants in the schema where appropriate, and avoid leaking ORM models into the domain/application contract.

## Alembic

**Why:** Makes PostgreSQL schema evolution reviewable, repeatable, and deployable.

**Owns:** Versioned migrations and schema changes.

**Must not own:** Runtime data workflows, backfills hidden inside request handling, or business orchestration.

**Constraints:** Every schema change has a migration; migrations must be safe to run in the documented deployment sequence.

## RabbitMQ

**Why:** Provides the asynchronous hand-off between ingestion and downstream processing.

**Owns:** Durable message delivery configuration, queues/exchanges, acknowledgements, and bounded retry/dead-letter behavior as specified.

**Must not own:** Binary payload storage, document metadata as the source of truth, authentication, or processing results.

**Constraints:** Messages carry `document_id`, `job_id`, and required execution metadata only. Publishing and database state must be coordinated so consumers do not receive unusable references; the chosen outbox or equivalent strategy must be documented before implementation.

## Firebase Authentication

**Why:** Provides email-based authentication without building an identity system in scope.

**Owns:** Identity proof and token verification.

**Must not own:** Document ownership records, ingestion authorization rules, document metadata, or processing state.

**Constraints:** The API verifies tokens and maps the stable Firebase user identifier to an authenticated principal. Secrets and project configuration come from environment variables. Provider-specific code stays at the infrastructure boundary.

## Firebase Storage

**Why:** Provides managed object storage suitable for immutable original artifacts and their storage references.

**Owns:** Binary artifact bytes, object paths, upload/download operations, and storage metadata needed by the adapter.

**Must not own:** Document registration, authorization policy, processing state, or semantic processing.

**Constraints:** Store originals under unique document-scoped paths, prevent accidental overwrite, verify size/hash as part of acceptance, and keep the storage adapter replaceable. Local filesystem or another object store may be used in tests through the same interface.

## Repository / Service architecture

The module structure follows `API -> application/service -> domain -> repository/infrastructure`.

* API owns HTTP concerns and authenticated request context.
* Application services orchestrate validation, transaction boundaries, artifact storage, registration, and job creation.
* Domain owns document, artifact, processing-state concepts and invariants without provider imports.
* Repositories hide PostgreSQL access.
* Infrastructure implements database sessions, Firebase adapters, RabbitMQ publishers, and format-specific technical inspection.

Use interfaces only at meaningful external boundaries: repositories, artifact storage, authentication, message publishing, and file validation/inspection. Do not add speculative ports, event buses, or microservices.

## Configuration and secrets

All environment-specific values come from environment variables loaded from a local `.env` during development and injected by the deployment environment in production. This includes PostgreSQL and RabbitMQ URLs, Firebase project/configuration, storage bucket, file limits, supported MIME types/extensions, queue names, retry settings, and environment name. `.env` files containing secrets are ignored and `.env.example` documents required names without credentials. No credentials or connection strings are hard-coded.

## Testing, linting, and formatting

Use pytest for unit, integration, and API tests. Use isolated PostgreSQL/RabbitMQ-backed integration environments where behavior depends on their guarantees; fake or local adapters are acceptable for focused unit tests. Use Ruff for linting and formatting, with configuration committed in project metadata. Tests must cover validation, ownership, immutability, transaction/recovery behavior, message shape, and non-blocking upload semantics.

## Dependency management

Use the repository's Python dependency manager and lockfile (currently `pyproject.toml` with `uv.lock`). Runtime and development dependencies must be declared there and kept reproducible. Do not add libraries without a documented responsibility in the scope.

## Containerization

Provide containerization only for reproducible local and deployment environments: an application image plus PostgreSQL and RabbitMQ service dependencies, with Firebase accessed through configured credentials or test doubles. Containers must receive configuration through environment variables and must not bake secrets into images.
