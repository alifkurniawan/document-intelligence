# Phase 1 Implementation Plan — Project Foundation

## Task group 1 — Establish the application package

1. Create the conventional `app/` package and the minimal bootstrap modules.
2. Create the initial `tests/` package and test configuration.
3. Keep future architectural directories minimal and free of speculative code.
4. Ensure imports work when the service is started from the repository root.

## Task group 2 — Implement the FastAPI bootstrap

1. Create the FastAPI application factory or module-level application entry point.
2. Add `GET /health` with the agreed 200 response and exact minimal JSON body.
3. Keep the endpoint independent of external services and authentication.
4. Add a clear local ASGI command to the project documentation.

## Task group 3 — Add baseline logging

1. Configure application logging at startup.
2. Use an environment-controlled log level with a safe default.
3. Avoid logging secrets, tokens, file contents, or sensitive request payloads.
4. Add a focused test or verification where logging configuration has observable behavior.

## Task group 4 — Align dependency and quality tooling

1. Review `pyproject.toml` and `uv.lock` for the Phase 1 runtime and development dependencies.
2. Add Ruff configuration and development dependency if absent.
3. Define consistent commands for formatting, linting, and tests.
4. Keep dependency changes limited to responsibilities required by this phase.

## Task group 5 — Add containerization

1. Create a Dockerfile for the FastAPI application using Python 3.14.
2. Use a reproducible dependency installation strategy based on the project lockfile.
3. Configure the container to run the API through an explicit command and expose its port.
4. Create a local Docker Compose file with the application and documented future dependency placeholders/profiles as appropriate.
5. Ensure no credentials are copied into the image or committed into Compose configuration.

## Task group 6 — Add CI workflow

1. Add a CI workflow for pull requests and the primary branch.
2. Install the locked dependencies in CI.
3. Run formatting/check, lint, and pytest commands.
4. Keep CI independent of production Firebase credentials, PostgreSQL, RabbitMQ, and external storage.
5. Cache dependencies only if the cache remains deterministic and does not hide failed installs.

## Task group 7 — Add tests and documentation

1. Test that the FastAPI application imports and starts.
2. Test `GET /health` returns HTTP 200 and `{"status":"ok"}`.
3. Document local setup, test, lint, format, Docker, and CI commands.
4. Document the Phase 1 boundary: foundation only, with no ingestion or Document Understanding.

## Task group 8 — Verify and prepare for handoff

1. Run the documented local quality commands.
2. Build and run the application container locally.
3. Verify the health endpoint from both the local process and container.
4. Review the diff for secrets, accidental binary inclusion, unrelated dependency changes, and public endpoints outside scope.
5. Confirm all validation criteria in `validation.md` before merge.
