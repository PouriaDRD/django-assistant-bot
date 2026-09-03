from __future__ import annotations


class ProjectError(Exception):
    """
    Base exception for project operations.
    """


class ProjectNotFoundError(ProjectError):
    """
    Raised when a project cannot be found.
    """


class ProjectAlreadyExistsError(ProjectError):
    """
    Raised when a project with the same name already exists.
    """


class ProjectValidationError(ProjectError):
    """
    Raised when project data violates business rules.
    """


class ProjectPersistenceError(ProjectError):
    """
    Raised when project persistence fails unexpectedly.
    """
