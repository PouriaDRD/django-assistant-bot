from __future__ import annotations


class SettingsError(Exception):
    """
    Base exception for application settings operations.
    """


class SettingsPersistenceError(SettingsError):
    """
    Raised when application settings persistence fails.
    """


class ProxyConfigurationError(SettingsError):
    """
    Raised when proxy settings are incomplete or invalid
    for the requested runtime operation.
    """


__all__ = [
    "ProxyConfigurationError",
    "SettingsError",
    "SettingsPersistenceError",
]
