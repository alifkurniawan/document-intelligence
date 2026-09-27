"""FastAPI application bootstrap."""

from __future__ import annotations

import logging
import logging.config

from fastapi import FastAPI

from app.config import Settings, get_settings


def configure_logging(settings: Settings | None = None) -> None:
    """Configure application logging once, without request or payload logging."""

    configured = settings or Settings()
    logging.basicConfig(
        level=getattr(logging, configured.log_level),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        force=True,
    )


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create the application with only the Phase 1 liveness endpoint."""

    configure_logging(settings or get_settings())
    application = FastAPI(title="Legal Document Intelligence Platform")

    @application.get("/health", response_model=dict[str, str])
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return application


app = create_app()
