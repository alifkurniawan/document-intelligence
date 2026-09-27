# Architecture and decisions

The service is a modular monolith with explicit provider boundaries:

```text
HTTP/FastAPI -> registration service -> domain entities
                         |                 |
             validation + storage     repositories / unit of work
                         |                 |
                 filesystem/Firebase  PostgreSQL metadata + outbox
                                                   |
                                             outbox dispatcher
                                                   |
                                                RabbitMQ
```

Routes own HTTP and authentication context. The application service coordinates
validation, original storage, metadata registration, and job creation. Provider-neutral
domain types own lifecycle and ownership invariants. Repositories hide SQLAlchemy and
transactions. Storage, Firebase Authentication, and RabbitMQ are replaceable adapters.

## Durable upload sequence

1. Firebase verifies the ID token and supplies the owner UID.
2. `FileValidator` hashes the input while checking filename, size, content MIME,
   extension, readability, and integrity.
3. A unique document-scoped original path is written to filesystem or Firebase
   Storage. The adapter verifies size and SHA-256 and refuses overwrite.
4. One document, original artifact, queued processing job, and reference-only outbox
   row are committed in one PostgreSQL unit of work.
5. An outbox dispatcher publishes the job reference after the database commit and
   marks the row published only after RabbitMQ publisher confirmation.
6. Downstream processing reads the original by reference and owns processing state
   transitions after the queued hand-off.

PostgreSQL stores metadata and storage references, never document bytes. RabbitMQ
messages contain identifiers and execution metadata, never document bytes. The
original is immutable source of truth and remains available for retry.

## Key decisions

- Original objects use `documents/{document_id}/original/{filename}` and are never
  silently overwritten.
- PostgreSQL metadata and RabbitMQ publication are coordinated with a transactional
  outbox; recovery retries durable pending rows through the normal publisher.
- The broker declares one durable processing exchange/queue and a durable DLQ. The
  message is reference-only and uses persistent delivery with publisher confirms.
- Processing permits three bounded exponential-backoff retries. Permanent failures
  and exhausted transient failures are dead-lettered and visible as `failed`.
- Filesystem storage and static token verification are appropriate local/test seams;
  production configuration requires Firebase Storage and Firebase settings.
- Batch/import remains a future adapter over the single-document service. Normalization
  remains deferred until a concrete downstream compatibility need exists.

The recovery policy is deliberately operator-triggered and dry-run-first. See the
[recovery runbook](recovery-runbook.md) for the operational source of truth.
