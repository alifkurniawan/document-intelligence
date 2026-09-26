# Technology Constitution

## Decision summary

The proposed stack is retained as the default because it matches the subsystem's Python-centric parsing requirements and supports clear separation between synchronous ingestion and asynchronous normalization. These are provisional decisions: each item has an explicit seam so operational evidence can justify a later replacement.

| Concern | Default | Decision rationale | Trade-off / trigger to revisit |
|---|---|---|---|
| Runtime | Python 3.12+ | Native ecosystem for the selected parsers and worker code. | CPU-heavy parsing and dependency isolation require worker limits and packaging discipline. |
| HTTP API | FastAPI | Typed async API, good multipart support, and direct Pydantic integration. | Async does not make CPU-bound parsing safe; parsing stays out of request handlers. |
| Persistence | PostgreSQL | Strong transactions, JSON support, constraints, and mature operational tooling. | Requires migrations, connection-pool management, and careful transaction boundaries. |
| ORM / data access | SQLAlchemy 2.x | Explicit transaction control and durable repository patterns. | More ceremony than a query-only layer; avoid hiding important locking/state queries. |
| API/domain schemas | Pydantic 2.x | Runtime validation and serialization aligned with FastAPI. | Keep persistence models separate from public contracts to avoid accidental coupling. |
| Authentication | Firebase Authentication | Managed user identity, sign-in providers, and short-lived Firebase ID tokens. The API verifies tokens with the Firebase Admin SDK and uses the Firebase UID as the actor identity. | Token verification depends on Firebase availability and credential/configuration hygiene; authorization rules must not rely on unverified client claims. |
| Object storage | Cloud Storage for Firebase | Firebase-backed Google Cloud Storage bucket for durable immutable bytes, streaming upload, and Firebase Storage path conventions. | Cloud Storage and PostgreSQL do not share a transaction; use pending records, explicit lifecycle states, and reconciliation. |
| Broker | RabbitMQ | Work queues, acknowledgements, retries, and routing fit normalization jobs. | Adds operations and delivery semantics; messages must be idempotent and small. |
| Worker | Python worker process | Reuses domain contracts and parser libraries without blocking API workers. | Requires deployment, timeout, concurrency, and poison-message handling. |
| PDF | PyMuPDF | Fast metadata/page inspection and text/layout access for PDFs. | Native dependencies and malformed/encrypted PDF edge cases need sandboxed handling. |
| Images | Pillow | Mature format detection and basic metadata/normalization support. | It is not OCR; decompression-bomb limits and pixel budgets are mandatory. |
| DOCX | python-docx | Practical extraction of paragraphs, tables, and document properties. | It does not fully model every OOXML feature; preserve the original and record unsupported content. |
| XLSX | openpyxl | Direct workbook/worksheet/cell access without requiring Excel. | Large or formula-heavy workbooks can be expensive; enforce row/cell limits and do not promise recalculation. |
| Migrations | Alembic | Standard SQLAlchemy migration workflow. | Migration review is required because schema state is operational state. |
| Testing | pytest + integration services | Contract, parser-fixture, API, worker, authentication, and failure-path coverage. | Requires representative adversarial fixtures and isolated Firebase emulator/storage and broker dependencies. |

## Architecture boundaries

The API owns Firebase authentication context, request validation, streaming intake, idempotency, and registration. It verifies the Firebase ID token before accepting a protected request, derives actor identity from the verified `uid`, and does not parse documents.

The application layer owns use cases and state transitions. It depends on ports for object storage, repositories, hashing, clock, and job publishing.

The worker owns format detection, parser invocation, normalization, artifact persistence, and status updates. It must be restartable and safe to run more than once for the same job.

The infrastructure layer owns FastAPI adapters, Firebase Admin initialization and ID-token verification, SQLAlchemy mappings, Cloud Storage client configuration, RabbitMQ topology, and parser adapters. Parser output must be mapped into an internal versioned normalization schema rather than exposed directly.

## Data and consistency model

Use a database record with a generated `document_id`, source metadata, hash, storage key/URI, lifecycle state, and timestamps. Add processing-attempt records rather than overwriting failure history. Persist a normalization artifact separately and link it to the source hash and normalizer version.

Cloud Storage for Firebase and PostgreSQL do not share a transaction. The registration workflow therefore needs explicit states such as `uploading`, `registered`, `processing`, `normalized`, `failed`, and `rejected`, plus a reconciliation command/job for orphaned objects or database rows. A transactional outbox is preferred for reliable job publication once the database is authoritative; if introduced, it is an architectural addition, not an invisible broker replacement.

Firebase Authentication is the identity provider, but PostgreSQL remains authoritative for document ownership, ingestion state, processing history, and application metadata. Store the verified Firebase `uid` and selected immutable identity snapshot fields needed for audit; never trust an actor ID supplied in the request body. Firebase custom claims may carry coarse roles, while resource-level authorization is enforced by the API against PostgreSQL ownership and policy data.

Source artifacts use a controlled path such as `documents/{document_id}/source/{safe_filename}` in the configured Firebase Storage bucket; the filename component must be sanitized or replaced with an opaque generated name. The backend uses Admin SDK/server credentials for ingestion and worker access; this server-side access is not a substitute for API authorization. Client-facing download or preview access, if added, must use short-lived signed URLs or an authorized backend proxy and must not expose bucket credentials.

## Technology alternatives and replacement policy

No technology is silently replaced in this constitution.

Potential future evaluations:

- Replace RabbitMQ with a managed queue when operational ownership, cross-region delivery, or elastic throughput outweighs RabbitMQ routing flexibility. Impact: change the job adapter and operational topology; retain the job contract and idempotency rules.
- Replace SQLAlchemy with a thinner SQL layer only if ORM behavior measurably obscures performance-critical queries. Impact: repository implementations change; domain models and migration ownership remain.
- Add a dedicated conversion service only if DOCX/XLSX fidelity or PDF rendering requirements exceed the selected libraries. Trade-off: improved fidelity versus latency, cost, data-transfer exposure, and a new availability dependency.
- Add OCR (for example, a separately governed OCR engine) only when scanned-PDF/image text extraction is in scope. It is not assumed by the current stack because OCR changes latency, privacy, quality evaluation, and artifact contracts.

Any replacement proposal must document the reason, trade-offs, interface impact, migration/backfill strategy, failure semantics, and rollback plan before implementation.

## Operational requirements

Configuration comes from environment-backed settings with safe defaults and no secrets in source control. Metrics must cover accepted/rejected uploads, bytes, queue depth, processing latency, parser failures, retries, and normalization success. Structured logs use correlation ID, document ID, attempt ID, and safe error code. Traces should cross API, database, storage, broker, and worker boundaries when the deployment platform supports them.

Firebase configuration must be environment-backed. Service-account credentials must be supplied through the deployment secret mechanism or workload identity, never committed to the repository or returned in API responses. Local tests should use the Firebase Auth and Storage emulators where practical.
