from __future__ import annotations


class AdminError(Exception):
    """
    Base exception for administrator service errors.
    """


class AdminValidationError(AdminError):
    """
    Administrator input is invalid.
    """


class AdminAlreadyExistsError(AdminError):
    """
    Administrator already exists.
    """


class AdminNotFoundError(AdminError):
    """
    Administrator does not exist.
    """


class LastAdminRemovalError(AdminError):
    """
    Removing the final administrator would lock the
    application.
    """


class AdminPersistenceError(AdminError):
    """
    Administrator persistence operation failed.
    """
