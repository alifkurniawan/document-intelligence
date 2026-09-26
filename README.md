# Legal Document Intelligence Platform

Phase 1 provides the runnable service foundation only. It exposes an unauthenticated
`GET /health` liveness endpoint and establishes the package, logging, test, container,
and CI seams for later ingestion phases. Document ingestion, persistence, storage,
authentication, messaging, and Document Understanding are intentionally out of scope.

## Local development

Python 3.14 and [uv](https://docs.astral.sh/uv/) are required.

```shell
uv sync --dev
uv run uvicorn app.main:app --reload
curl http://127.0.0.1:8000/health
```

The response is `{"status":"ok"}`. Set `LOG_LEVEL` to `DEBUG`, `INFO`, `WARNING`,
or another standard level to control local logging; it defaults to `INFO`.

## Quality checks

```shell
uv run ruff format --check .
uv run ruff check .
uv run pytest
```

To format files, run `uv run ruff format .`.

## Container

The image uses the locked dependency set and does not copy environment files or
credentials:

```shell
docker build -t legal-document-backend .
docker run --rm -p 8000:8000 legal-document-backend
```

The foundation Compose profile runs the application only:

```shell
docker compose --profile foundation up --build
```

PostgreSQL and RabbitMQ are declared under the `future` profile as placeholders for
later phases and are not consumed by the Phase 1 application.

## CI

GitHub Actions runs locked dependency installation, Ruff formatting/linting, and the
pytest suite for pull requests and pushes to `main`. It requires no external service
credentials.

