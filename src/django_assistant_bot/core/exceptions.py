from __future__ import annotations


class ApplicationError(Exception):
    """
    Base exception for application-level errors.
    """


# ==========================================================
# Environment
# ==========================================================


class EnvironmentError(ApplicationError):
    """
    Base exception for environment errors.
    """


class EnvironmentValidationError(EnvironmentError):
    """
    Raised when environment configuration is invalid.
    """


# ==========================================================
# Database
# ==========================================================


class DatabaseError(ApplicationError):
    """
    Base exception for database errors.
    """


class DatabaseConnectionError(DatabaseError):
    """
    Raised when a SQLite operation or connection fails.
    """


class DatabaseInitializationError(DatabaseError):
    """
    Raised when the database cannot be initialized.
    """


# ==========================================================
# Migrations
# ==========================================================


class MigrationError(DatabaseError):
    """
    Base exception for database migration errors.
    """


class MigrationFileError(MigrationError):
    """
    Raised when a migration file cannot be read.
    """


class MigrationExecutionError(MigrationError):
    """
    Raised when a migration cannot be executed.
    """
