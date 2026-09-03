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

    def get_settings(
        self,
    ) -> AppSettingsSchema:
        try:
            return self._repository.get()

        except PersistenceError as exc:
            raise SettingsPersistenceError(
                "Could not load application settings."
            ) from exc

    def update_settings(
        self,
        data: AppSettingsUpdateSchema,
    ) -> AppSettingsSchema:
        try:
            return self._repository.update(
                data,
            )

        except PersistenceError as exc:
            raise SettingsPersistenceError(
                "Could not update application settings."
            ) from exc
