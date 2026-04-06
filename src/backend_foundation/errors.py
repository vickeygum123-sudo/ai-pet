"""Domain-level backend foundation errors."""


class DomainError(Exception):
    """Base exception for backend foundation rule violations."""


class NotFoundError(DomainError):
    """Raised when a requested account, device, binding, or session is missing."""


class ConflictError(DomainError):
    """Raised when a rule conflict prevents the requested action."""
