"""Stable application errors for mapping ingestion failures to HTTP responses."""


class IngestionError(RuntimeError):
    """Base error for an ingestion operation."""


class ValidationError(IngestionError):
    """The submitted file is not an accepted technical document."""


class AuthenticationError(IngestionError):
    """The authentication credential is absent or invalid."""


class StorageError(IngestionError):
    """The artifact storage boundary could not complete an operation."""


class AuthorizationError(IngestionError):
    """The authenticated owner is not allowed to access a resource."""


class NotFoundError(IngestionError):
    """The requested resource does not exist or is not visible to the owner."""


class DependencyError(IngestionError):
    """An external dependency prevented a safe operation."""
