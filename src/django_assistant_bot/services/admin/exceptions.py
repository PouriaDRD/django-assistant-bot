from __future__ import annotations


class AdminError(Exception):
    """Base exception for administrator operations."""


class AdminAlreadyExistsError(AdminError):
    """Raised when an administrator already exists."""


class AdminNotFoundError(AdminError):
    """Raised when an administrator cannot be found."""


class AdminValidationError(AdminError):
    """Raised when administrator data is invalid."""


class AdminPersistenceError(AdminError):
    """Raised when administrator persistence fails."""
