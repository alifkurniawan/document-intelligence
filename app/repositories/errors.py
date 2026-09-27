"""Stable repository-layer errors."""


class RepositoryError(RuntimeError):
    """Base repository error."""


class EntityNotFound(RepositoryError):
    """Raised when a requested entity does not exist in the repository."""


class RepositoryConflict(RepositoryError):
    """Raised when a persistence constraint is violated."""
