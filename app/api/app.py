"""FastAPI application bootstrap."""

from __future__ import annotations

import logging
import logging.config

from fastapi import FastAPI, Request
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.api.auth import AuthenticatedOwner, TokenVerifier
from app.api.exception_handlers import register_exception_handlers
from app.api.routes.authentication import create_auth_router
from app.api.routes.documents import create_document_router
from app.core.config import Settings, get_settings
from app.core.database import create_engine
from app.core.observability import (
    CorrelationFilter,
    new_correlation_id,
    set_correlation_id,
)
from app.repositories.document import SqlAlchemyMetadataUnitOfWork
from app.schemas.responses import ApiResponse
from app.services.authentication import ApplicationTokenService, AuthenticationService
from app.services.document_ingestion import DocumentIngestionService
from app.services.document_management import DocumentManagementService
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
    application.state.document_management_service = None
    application.state.token_verifier = None
    application.state.application_token_service = ApplicationTokenService(configured)
    application.state.authentication_service = None
    register_exception_handlers(application)

    @application.middleware("http")
    async def correlation_middleware(request: Request, call_next):
        request_id = new_correlation_id(request.headers.get("X-Correlation-ID"))
        set_correlation_id(request_id)
        response = await call_next(request)
        response.headers["X-Correlation-ID"] = request_id
        return response

    @application.get("/health", response_model=ApiResponse[dict[str, str]])
    async def health() -> ApiResponse[dict[str, str]]:
        return ApiResponse(data={"status": "ok"}, message="Service is healthy.")

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
            token_service = application.state.application_token_service

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
            application.state.authentication_service = AuthenticationService(
                factory,
                configured,
                token_service=application.state.application_token_service,
            )
        if application.state.authentication_service is not None:
            get_token_verifier()
        return application.state.authentication_service

    def get_document_management_service() -> DocumentManagementService | None:
        if application.state.document_management_service is None:
            ingestion_service = get_registration_service()
            if ingestion_service is None:
                return None
            application.state.document_management_service = DocumentManagementService(
                unit_of_work_factory=ingestion_service.unit_of_work_factory,
                storage=ingestion_service.storage,
            )
        return application.state.document_management_service

    application.include_router(
        create_document_router(
            get_registration_service=get_registration_service,
            get_document_management_service=get_document_management_service,
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
