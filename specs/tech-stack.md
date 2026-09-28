# Tech Stack

## Baseline

The current backend uses Python 3.14, FastAPI, PostgreSQL, SQLAlchemy, Alembic, RabbitMQ, Firebase Authentication, and Firebase Storage. The implementation is a modular monolith: `app/api` exposes the HTTP boundary, `app/services` orchestrates use cases, `app/models` contains entities and persistence models, `app/repositories` handles metadata persistence, `app/storage` handles binary artifacts, and `app/workers` handles asynchronous publication. Infrastructure choices remain behind interfaces where replacement is practical; they are not domain concepts.

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

## Document Understanding processing

Document Understanding is a subsequent asynchronous processing capability after
Document Ingestion. Ingestion remains responsible for authentication and
authorization, technical validation, document registration, immutable original
storage, metadata, processing-job creation, and asynchronous hand-off. Understanding
consumes the original by reference and must not modify or replace it.

Processing follows these architectural stages:

```text
inspection -> processor selection -> content extraction -> OCR when required
-> structure/layout -> Document Representation -> provenance -> semantic extraction
```

Processor selection is based on document characteristics and uses the simplest
appropriate method. Text PDFs use text/PDF parsing where adequate; scanned PDFs and
images may use OCR; DOCX uses a DOCX parser; and XLSX uses a spreadsheet parser.
OCR is a first-class capability, with PaddleOCR as the preferred initial
implementation. The processing boundary must remain replaceable and must not become
dependent on PaddleOCR-specific details. VLM/LLM processing is optional and is not
mandatory; it is introduced only for a concrete requirement that simpler or
specialized processing cannot adequately address.

Document Representation is a structured, machine-readable view of document content
and observable structure. It may contain document information, pages, text blocks,
headings, paragraphs, tables, images, reading order, layout, coordinates, and
provenance. Structure and semantics remain distinct: structure records what exists,
while semantic extraction identifies meaning such as people, organizations,
addresses, dates, monetary amounts, property, clauses, obligations, and
relationships. Semantic extraction operates on the representation, never on a
mutable replacement of the original artifact.

Original artifacts, intermediate data, and derived semantic data are distinct. OCR
results, extracted text, page images, layout information, and parsed structure may
be retained as intermediate outputs, but none may replace the original. Derived
information should remain traceable to its source whenever practical, including
applicable document/artifact version, page or block, bounding box, source text,
processor/version, model/version, prompt version, extraction-logic version, and
processing timestamp. The requirement is traceability, not a rigid field set for
every processor.

Processing results are version-aware where applicable and can be reprocessed from an
existing immutable original when processing logic changes, without requiring a new
upload. Processing status, transient failure handling, bounded retry, permanent
failure reporting, and reprocessing remain compatible with the existing RabbitMQ
hand-off and do not require a new workflow engine.

Application services and processing components use Dependency Injection to remain
testable and maintainable. Dependency Injection does not require speculative ports,
adapters, factories, layers, or other abstractions beyond meaningful boundaries.

## Package architecture

The current package structure follows this flow:

```text
API routes/schemas + auth
          |
          v
application services (ingestion, validation, recovery)
          |
          +--> models/entities ---------> repositories -> PostgreSQL metadata/outbox
          |
          +--> storage/artifacts --------> filesystem or Firebase Storage
          |
          +--> workers/contracts --------> RabbitMQ publisher -> downstream consumer
          |
          +--> core/config, database, observability, provider initialization
```

* `app/api` owns FastAPI bootstrap, routes, authentication context, and HTTP mapping.
* `app/core` owns settings, database setup, Firebase initialization, observability, and shared errors.
* `app/models` owns provider-neutral entities plus SQLAlchemy database models.
* `app/services` owns validation, ingestion orchestration, and recovery workflows.
* `app/repositories` owns SQLAlchemy repositories and `SqlAlchemyMetadataUnitOfWork`.
* `app/storage` owns the artifact-storage protocol and filesystem/Firebase adapters.
* `app/workers` owns processing contracts, RabbitMQ integration, outbox dispatch, and worker runtime.
* `app/schemas` owns API response models.

The API process and outbox worker are separate runtimes of the same modular monolith, not separate domain services. Use interfaces only at meaningful external boundaries: authentication, repositories/unit of work, artifact storage, message publishing, and validation/inspection. Do not add speculative ports, event buses, or microservices.

Adding Document Understanding does not change the modular-monolith decision. It does
not introduce requirements for microservices, Clean Architecture, Hexagonal
Architecture, CQRS, event sourcing, multi-agent systems, autonomous agents, or agent
frameworks. Downstream intelligence such as RAG, vector search, question answering,
comparison, legal analysis, Shariah analysis, risk analysis, and recommendations is
outside this capability.

## Configuration and secrets

All environment-specific values come from environment variables loaded from a local `.env` during development and injected by the deployment environment in production. This includes PostgreSQL and RabbitMQ URLs, Firebase project/configuration, storage bucket, file limits, supported MIME types/extensions, queue names, retry settings, and environment name. `.env` files containing secrets are ignored and `.env.example` documents required names without credentials. No credentials or connection strings are hard-coded.

## Testing, linting, and formatting

Use pytest for unit, integration, and API tests. Use isolated PostgreSQL/RabbitMQ-backed integration environments where behavior depends on their guarantees; fake or local adapters are acceptable for focused unit tests. Use Ruff for linting and formatting, with configuration committed in project metadata. Tests must cover validation, ownership, immutability, transaction/recovery behavior, message shape, and non-blocking upload semantics.

## Dependency management

Use the repository's Python dependency manager and lockfile (currently `pyproject.toml` with `uv.lock`). Runtime and development dependencies must be declared there and kept reproducible. Do not add libraries without a documented responsibility in the scope.

## Containerization

Provide containerization only for reproducible local and deployment environments: an application image plus PostgreSQL and RabbitMQ service dependencies, with Firebase accessed through configured credentials or test doubles. Containers must receive configuration through environment variables and must not bake secrets into images.
