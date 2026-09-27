# Document Understanding boundary

Ingestion performs technical acceptance only: authentication, ownership, filename and
MIME checks, size limits, readability/integrity checks, hashing, immutable storage,
metadata registration, and asynchronous hand-off.

It does not perform or require OCR, VLM/LLM understanding, classification, entity or
clause extraction, obligation extraction, embeddings, RAG, legal analysis, Shariah
analysis, or other semantic interpretation. A scanned PDF is preserved as uploaded;
its text is not extracted by this service.

Any downstream processor must consume the immutable original through its reference and
write its own results without changing the original artifact or the ingestion metadata
contract. Technical normalization is deferred until a concrete compatibility need is
recorded with lineage and tests.
