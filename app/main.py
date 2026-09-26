"""FastAPI application bootstrap."""

from __future__ import annotations

import logging
import logging.config
import os

from fastapi import FastAPI


def _log_level() -> str:
    """Return a safe, normalized log level from the environment."""

    configured = os.getenv("LOG_LEVEL", "INFO").upper()
    return configured if isinstance(getattr(logging, configured, None), int) else "INFO"


def configure_logging() -> None:
    """Configure application logging once, without request or payload logging."""

    logging.basicConfig(
        level=getattr(logging, _log_level()),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        force=True,
    )


def create_app() -> FastAPI:
    """Create the application with only the Phase 1 liveness endpoint."""

    configure_logging()
    application = FastAPI(title="Legal Document Intelligence Platform")

    @application.get("/health", response_model=dict[str, str])
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return application


app = create_app()
