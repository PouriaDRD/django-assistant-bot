from __future__ import annotations


class RepositoryError(Exception):
    """
    Base exception for persistence operations.
    """


class EntityNotFoundError(RepositoryError):
    """
    Raised when an expected database entity
    does not exist.
    """


class DuplicateEntityError(RepositoryError):
    """
    Raised when a unique entity already exists.
    """


class PersistenceError(RepositoryError):
    """
    Raised when persistence fails unexpectedly.
    """
