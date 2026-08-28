from __future__ import annotations

from dataclasses import dataclass

from config.models import AppConfig
from config.settings_manager import SettingsManager


@dataclass(slots=True)
class ApplicationContext:
    """
    Runtime dependencies shared across the application.
    """

    settings: SettingsManager
    config: AppConfig

    def reload_config(self) -> AppConfig:
        """
        Reload configuration from disk.
        """
        self.config = self.settings.load()
        return self.config

    def save_config(
        self,
        config: AppConfig,
    ) -> AppConfig:
        """
        Persist and update the active application configuration.
        """
        self.settings.save(config)
        self.config = config
        return self.config
