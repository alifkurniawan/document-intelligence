# Phase 1 — Domain contracts plan

1. Define the supported-format contract for PDF, scanned PDF, PNG, JPEG, DOCX, and XLSX, including stable identifiers and validation-facing metadata.
2. Define the canonical `Document Object` contract from `specs/mission.md`, including source metadata, actor metadata, storage identity, and processing status.
3. Define lifecycle status values and allowed transitions, including rejected and failed outcomes, the distinction between document state and processing-attempt state, the two-attempt failed retry rule, and explicit approval for normalized reprocessing.
4. Define stable error codes and the error envelope used by application and infrastructure boundaries.
5. Define processing-job and normalization-artifact contracts, including document identity, source hash, attempt identity, normalizer version, and correlation data.
6. Implement Pydantic 2.x models without infrastructure imports, then add serialization and invalid-state tests.
7. Review compatibility, naming, nullability, and versioning decisions before downstream database and API work begins.
