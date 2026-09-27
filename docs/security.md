# Security notes

- Firebase ID tokens are verified by the Firebase adapter; the stable Firebase UID is
  the owner identity. Missing, invalid, or owner-mismatched requests are rejected.
- Document reads are owner-scoped. PostgreSQL records metadata and references only;
  binary contents stay in the configured artifact store.
- Filenames reject traversal/path separators and NUL bytes. Validation uses detected
  content MIME, extension allowlists, size limits, readability, integrity checks, and
  SHA-256 verification.
- Original paths are document-scoped and exclusive. Processing and normalization must
  never replace the original.
- RabbitMQ payloads contain document/job/artifact identifiers and execution metadata,
  never tokens, credentials, or file bytes.
- Logs include safe identifiers and correlation IDs but must not include authorization
  headers, tokens, document contents, or secret configuration. Public errors are
  generic where provider details would be sensitive.
- Secrets belong in a deployment secret manager or injected environment. `.env`,
  Firebase credentials, production URLs, and test fixtures containing real documents
  must not be committed.
- Use least-privilege database, broker, Firebase, and storage identities. Restrict
  network access to the API and dependency endpoints and protect broker management
  interfaces.

Security incidents or ambiguous ownership/storage state are stop-and-escalate events;
use correlation ID, document ID, job ID, and outbox ID to investigate without copying
tokens or document bytes into tickets.
