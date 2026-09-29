FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN pip install --no-cache-dir uv \
    && uv sync --frozen --no-dev --no-install-project

COPY app ./app
COPY src ./src
COPY alembic.ini ./alembic.ini
COPY alembic ./alembic

EXPOSE 8000
CMD ["uv", "run", "--no-sync", "uvicorn", "app.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
