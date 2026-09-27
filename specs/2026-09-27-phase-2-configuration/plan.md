# Phase 2 Implementation Plan — Configuration

## Task group 1 — Define the configuration contract

1. Inventory every environment-driven setting required by the current service and the Phase 2 roadmap scope, using unprefixed uppercase underscore-separated names.
2. Group settings by runtime, application limits, supported formats, PostgreSQL, RabbitMQ, Firebase Authentication, Firebase Storage, and environment identity.
3. Define names, types, defaults, requiredness, and safe representations for secrets and connection strings.
4. Record the `development`, `test`, and `production` modes and the confirmed retry policy in `requirements.md`.

## Task group 2 — Implement typed settings

1. Add a single application settings module as the source of truth for configuration access.
2. Use typed parsing and validation for URLs, booleans, integers, lists, enums, MIME types, extensions, and size limits.
3. Load local development values from `.env` where supported, while allowing deployment-injected environment variables to take precedence.
4. Keep settings provider-neutral and do not instantiate database, Firebase, storage, or RabbitMQ clients during settings import.

## Task group 3 — Validate environment-specific requirements

1. Define a development/test mode that can run without production credentials when the test strategy allows it.
2. Make production-required settings fail clearly at startup or settings construction when absent or invalid.
3. Prevent insecure combinations such as missing storage configuration, invalid size limits, or empty allowlists in modes where they are required.
4. Ensure validation errors identify the setting and reason without exposing secret values.

## Task group 4 — Add configuration documentation and examples

1. Add or update `.env.example` with all supported variable names and safe placeholder values.
2. Document defaults, requiredness, allowed values, and local setup in the project documentation or configuration reference.
3. Document which settings are consumed now versus reserved for later phases.
4. Do not commit credentials, service-account contents, or real connection strings.

## Task group 5 — Test configuration behavior

1. Test default values and explicit environment overrides.
2. Test parsing and normalization of supported setting formats, including API/logging settings, upload policy, and RabbitMQ retry/DLQ policy.
3. Test missing and invalid required values produce deterministic, actionable errors.
4. Test secret-bearing settings are not included in ordinary repr/log output.
5. Test settings construction does not require external services or network access.

## Task group 6 — Verify and prepare for handoff

1. Run formatting, lint, and the full test suite using the repository commands.
2. Review the resulting environment surface for unnecessary or speculative settings.
3. Check the diff for secrets, accidental credential files, and unrelated changes.
4. Confirm every validation criterion in `validation.md` before merge.
