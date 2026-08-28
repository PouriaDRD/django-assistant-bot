class ConfigError(Exception):
    """Base exception for configuration errors."""


class ConfigFileNotFoundError(ConfigError):
    """Raised when the configuration file does not exist."""


class ConfigValidationError(ConfigError):
    """Raised when configuration validation fails."""


class ConfigWriteError(ConfigError):
    """Raised when configuration cannot be written."""


class ProjectError(Exception):
    """Base exception for project operations."""


class ProjectNotFoundError(ProjectError):
    """Raised when a project cannot be found."""


class ProjectAlreadyExistsError(ProjectError):
    """Raised when a project already exists."""


class ProjectValidationError(ProjectError):
    """Raised when project data is invalid."""
