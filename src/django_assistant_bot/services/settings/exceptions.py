from __future__ import annotations


class SettingsError(Exception):
    """Base exception for application settings operations."""


class SettingsPersistenceError(SettingsError):
    """Raised when application settings persistence fails."""
