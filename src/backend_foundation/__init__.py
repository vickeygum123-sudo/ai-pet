"""Framework-agnostic backend foundation for the MVP device/session workstream."""

from .application import RepositoryBackedBackendFoundationService
from .errors import DomainError
from .models import FailureCode
from .service import BackendFoundationService

__all__ = [
    "BackendFoundationService",
    "RepositoryBackedBackendFoundationService",
    "DomainError",
    "FailureCode",
]
