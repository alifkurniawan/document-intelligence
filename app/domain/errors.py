"""Domain-level errors independent from infrastructure providers."""


class DomainError(ValueError):
    """Base error for an invalid domain operation or value."""


class InvalidStateTransition(DomainError):
    """Raised when an entity cannot move between the requested states."""


class OwnershipError(DomainError):
    """Raised when an operation targets a document owned by another account."""


class OriginalArtifactError(DomainError):
    """Raised when original-artifact provenance would be invalidated."""
