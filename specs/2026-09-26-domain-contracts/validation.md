# Phase 1 — Domain contracts validation

The phase is ready to merge when all of the following are true:

1. Every contract can be imported without starting FastAPI, PostgreSQL, Firebase, Cloud Storage, RabbitMQ, or a parser.
2. Supported-format values, lifecycle statuses, error codes, processing jobs, normalization artifacts, and the canonical `Document Object` serialize deterministically through Pydantic.
3. Serialization preserves required identifiers, source filename/media type/size/hash, storage URI, actor metadata, timestamps, status, attempt identity, and normalizer version where applicable.
4. Invalid values are rejected deterministically, including unsupported formats, malformed hashes or UUIDs, negative sizes, naive timestamps, missing required identity fields, and impossible status values.
5. Tests cover required fields, optional/null fields, enum/string compatibility decisions, round-trip serialization, and representative valid fixtures for all six supported source formats.
6. Tests cover malformed and adversarial contract inputs without requiring external services.
7. Lifecycle transition rules and error-code semantics are documented and tested, including strict UUIDs, timezone-aware timestamps, the two-attempt failed retry rule, and explicit approval for normalized reprocessing.
8. Contract tests establish the compatibility policy for future schema changes and versioned normalization artifacts.
9. The full project test and lint commands pass, and the resulting changes are limited to the Phase 1 contract implementation and its tests.

## Merge gate

An implementation may be merged into `main` only after the open decisions in `requirements.md` are resolved, the contract tests pass, and a reviewer confirms that no infrastructure or parser behavior has leaked into the domain layer.
