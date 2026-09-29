"""FastAPI application bootstrap."""

from __future__ import annotations

import logging
import logging.config

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.api.auth import AuthenticatedOwner, TokenVerifier
from app.api.routes.authentication import create_auth_router
from app.api.routes.documents import create_document_router
from app.core.config import Settings, get_settings
from app.core.database import create_engine
from app.core.observability import (
    CorrelationFilter,
    correlation_id,
    metrics,
    new_correlation_id,
    set_correlation_id,
)
from app.repositories.document import SqlAlchemyMetadataUnitOfWork
from app.services.authentication import ApplicationTokenService, AuthenticationService
from app.services.document_ingestion import DocumentIngestionService
from app.services.validation import FileValidator


def configure_logging(settings: Settings | None = None) -> None:
    """Configure application logging once, without request or payload logging."""

    configured = settings or Settings()
    logging.basicConfig(
        level=getattr(logging, configured.log_level),
        format="%(asctime)s %(levelname)s %(name)s %(message)s correlation_id=%(correlation_id)s",
        force=True,
    )
    for handler in logging.getLogger().handlers:
        handler.addFilter(CorrelationFilter())


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create the API and keep provider orchestration outside route handlers."""

    configured = settings or get_settings()
    configure_logging(configured)
    application = FastAPI(title="Legal Document Intelligence Platform")
    application.state.settings = configured
    application.state.registration_service = None
    application.state.token_verifier = None
    application.state.authentication_service = None

    @application.middleware("http")
    async def correlation_middleware(request: Request, call_next):
        request_id = new_correlation_id(request.headers.get("X-Correlation-ID"))
        set_correlation_id(request_id)
        response = await call_next(request)
        response.headers["X-Correlation-ID"] = request_id
        return response

    @application.exception_handler(HTTPException)
    async def http_error_handler(request: Request, exc: HTTPException):
        detail = (
            exc.detail
            if isinstance(exc.detail, dict)
            else {"code": "http_error", "detail": str(exc.detail)}
        )
        request_id = correlation_id()
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "code": detail.get("code", "http_error"),
                "detail": detail.get("detail", "request failed"),
                "correlation_id": request_id,
            },
            headers={"X-Correlation-ID": request_id},
        )

    @application.exception_handler(RequestValidationError)
    async def request_validation_error_handler(request: Request, exc: RequestValidationError):
        request_id = correlation_id()
        metrics.increment("api_validation_failures")
        return JSONResponse(
            status_code=422,
            content={
                "code": "invalid_request",
                "detail": "request validation failed",
                "correlation_id": request_id,
            },
            headers={"X-Correlation-ID": request_id},
        )

    @application.exception_handler(Exception)
    async def unexpected_error_handler(request: Request, exc: Exception):
        logging.getLogger(__name__).exception("unhandled request failure")
        metrics.increment("api_unexpected_failures")
        request_id = correlation_id()
        return JSONResponse(
            status_code=500,
            content={
                "code": "internal_error",
                "detail": "internal server error",
                "correlation_id": request_id,
            },
            headers={"X-Correlation-ID": request_id},
        )

    @application.get("/health", response_model=dict[str, str])
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    def get_registration_service() -> DocumentIngestionService:
        if application.state.registration_service is None:
            if configured.database_url is None:
                return None
            engine = create_engine(configured)
            factory = async_sessionmaker(engine, expire_on_commit=False)
            from app.storage.artifacts import FilesystemArtifactStorage, FirebaseArtifactStorage

            storage = (
                FirebaseArtifactStorage(configured.firebase_storage_bucket, configured)
                if configured.storage_backend == "firebase" and configured.firebase_storage_bucket
                else FilesystemArtifactStorage(configured.storage_root)
            )
            application.state.registration_service = DocumentIngestionService(
                validator=FileValidator(configured),
                storage=storage,
                unit_of_work_factory=lambda: SqlAlchemyMetadataUnitOfWork(factory),
                routing_key=configured.rabbitmq_routing_key,
            )
        return application.state.registration_service

    def get_token_verifier() -> TokenVerifier:
        if application.state.token_verifier is None:
            token_service = ApplicationTokenService(configured)

            class ApplicationAccessTokenVerifier:
                async def verify(self, token: str) -> AuthenticatedOwner:
                    user_id, firebase_uid = token_service.verify_access_token(token)
                    return AuthenticatedOwner(owner_id=str(user_id), firebase_uid=firebase_uid)

            application.state.token_verifier = ApplicationAccessTokenVerifier()
        return application.state.token_verifier

    def get_authentication_service() -> AuthenticationService | None:
        if application.state.authentication_service is None and configured.database_url is not None:
            engine = create_engine(configured)
            factory = async_sessionmaker(engine, expire_on_commit=False)
            application.state.authentication_service = AuthenticationService(factory, configured)
        if application.state.authentication_service is not None:
            get_token_verifier()
        return application.state.authentication_service

    def get_unit_of_work_factory():
        service = get_registration_service()
        return service.unit_of_work_factory if service is not None else None

    application.include_router(
        create_document_router(
            get_registration_service=get_registration_service,
            get_token_verifier=get_token_verifier,
            get_uow_factory=get_unit_of_work_factory,
        )
    )
    application.include_router(
        create_auth_router(
            get_auth_service=get_authentication_service, get_settings=lambda: configured
        )
    )
    get_token_verifier()

    return application


app = create_app()
