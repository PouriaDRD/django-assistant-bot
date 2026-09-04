from __future__ import annotations

from django_assistant_bot.repositories.app_settings import (
    AppSettingsRepository,
)
from django_assistant_bot.repositories.exceptions import (
    PersistenceError,
)
from django_assistant_bot.schemas.app_settings import (
    AppSettingsSchema,
    AppSettingsUpdateSchema,
)
from django_assistant_bot.services.settings.exceptions import (
    SettingsPersistenceError,
)


class AppSettingsService:
    """
    Application service for runtime settings.

    Secrets and bootstrap configuration do not belong here.
    They are provided by EnvironmentSettings.
    """

    def __init__(
        self,
        repository: AppSettingsRepository,
    ) -> None:
        self._repository = repository

    # =====================================================
    # READ
    # =====================================================

    def get_settings(
        self,
    ) -> AppSettingsSchema:
        """
        Return persisted application settings.
        """

        try:
            return self._repository.get()

        except PersistenceError as exc:
            raise SettingsPersistenceError(
                "Could not load application settings."
            ) from exc

    def is_bot_enabled(
        self,
    ) -> bool:
        """
        Return whether application activity is enabled.
        """

        return self.get_settings().bot_enabled

    # =====================================================
    # GENERIC UPDATE
    # =====================================================

    def update_settings(
        self,
        data: AppSettingsUpdateSchema,
    ) -> AppSettingsSchema:
        """
        Partially update persisted application settings.
        """

        try:
            return self._repository.update(
                data,
            )

        except PersistenceError as exc:
            raise SettingsPersistenceError(
                "Could not update application settings."
            ) from exc

    # =====================================================
    # BOT STATE
    # =====================================================

    def enable_bot(
        self,
    ) -> AppSettingsSchema:
        """
        Enable application activity.
        """

        return self.update_settings(
            AppSettingsUpdateSchema(
                bot_enabled=True,
            )
        )

    def disable_bot(
        self,
    ) -> AppSettingsSchema:
        """
        Disable application activity globally.
        """

        return self.update_settings(
            AppSettingsUpdateSchema(
                bot_enabled=False,
            )
        )

    # =====================================================
    # BACKUP STATE
    # =====================================================

    def enable_backups(
        self,
    ) -> AppSettingsSchema:
        """
        Enable global backup functionality.
        """

        return self.update_settings(
            AppSettingsUpdateSchema(
                backup_enabled=True,
            )
        )

    def disable_backups(
        self,
    ) -> AppSettingsSchema:
        """
        Disable global backup functionality.
        """

        return self.update_settings(
            AppSettingsUpdateSchema(
                backup_enabled=False,
            )
        )

    # =====================================================
    # RETENTION STATE
    # =====================================================

    def enable_retention(
        self,
    ) -> AppSettingsSchema:
        """
        Enable automatic backup retention cleanup.
        """

        return self.update_settings(
            AppSettingsUpdateSchema(
                retention_enabled=True,
            )
        )

    def disable_retention(
        self,
    ) -> AppSettingsSchema:
        """
        Disable automatic backup retention cleanup.
        """

        return self.update_settings(
            AppSettingsUpdateSchema(
                retention_enabled=False,
            )
        )

    def set_retention_keep_last(
        self,
        keep_last: int,
    ) -> AppSettingsSchema:
        """
        Set the number of successful backups retained
        per project.
        """

        return self.update_settings(
            AppSettingsUpdateSchema(
                retention_keep_last=keep_last,
            )
        )


__all__ = [
    "AppSettingsService",
]
