"""Application-facing single-document ingestion contracts and services."""

from app.ingestion.auth import (
    AuthenticatedOwner,
    FirebaseAuthVerifier,
    StaticTokenVerifier,
    TokenVerifier,
)
from app.ingestion.errors import (
    AuthenticationError,
    IngestionError,
    StorageError,
    ValidationError,
)
from app.ingestion.registration import DocumentRegistrationService, RegistrationResult
from app.ingestion.storage import (
    ArtifactStorage,
    FilesystemArtifactStorage,
    FirebaseArtifactStorage,
    InMemoryArtifactStorage,
    StoredArtifact,
)
from app.ingestion.validation import FileValidator, ValidatedFile

__all__ = [
    "ArtifactStorage",
    "AuthenticatedOwner",
    "AuthenticationError",
    "DocumentRegistrationService",
    "FirebaseArtifactStorage",
    "FirebaseAuthVerifier",
    "FileValidator",
    "FilesystemArtifactStorage",
    "InMemoryArtifactStorage",
    "IngestionError",
    "RegistrationResult",
    "StorageError",
    "StoredArtifact",
    "StaticTokenVerifier",
    "TokenVerifier",
    "ValidatedFile",
    "ValidationError",
]
