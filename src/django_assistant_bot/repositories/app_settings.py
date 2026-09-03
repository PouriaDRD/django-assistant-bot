from __future__ import annotations

from pathlib import Path

from sqlalchemy.exc import SQLAlchemyError

from django_assistant_bot.database.models.app_settings import (
    AppSettingsModel,
)
from django_assistant_bot.database.session import SessionManager
from django_assistant_bot.repositories.exceptions import (
    PersistenceError,
)
from django_assistant_bot.schemas.app_settings import (
    AppSettingsSchema,
    AppSettingsUpdateSchema,
)


class AppSettingsRepository:
    SETTINGS_ID = 1

    def __init__(
        self,
        sessions: SessionManager,
    ) -> None:
        self._sessions = sessions

    def get(self) -> AppSettingsSchema:
        try:
            with self._sessions.transaction() as session:
                model = session.get(
                    AppSettingsModel,
                    self.SETTINGS_ID,
                )

                if model is None:
                    model = AppSettingsModel(
                        id=self.SETTINGS_ID,
                    )

                    session.add(model)
                    session.flush()

                settings = self._to_schema(model)

            return settings

        except SQLAlchemyError as exc:
            raise PersistenceError("Could not load application settings.") from exc

    def update(
        self,
        data: AppSettingsUpdateSchema,
    ) -> AppSettingsSchema:
        try:
            with self._sessions.transaction() as session:
                model = session.get(
                    AppSettingsModel,
                    self.SETTINGS_ID,
                )

                if model is None:
                    model = AppSettingsModel(
                        id=self.SETTINGS_ID,
                    )

                    session.add(model)
                    session.flush()

                values = data.model_dump(
                    exclude_none=True,
                )

                for field_name, value in values.items():
                    if field_name == ("backup_directory"):
                        value = str(value)

                    setattr(
                        model,
                        field_name,
                        value,
                    )

                session.flush()

                settings = self._to_schema(model)

            return settings

        except SQLAlchemyError as exc:
            raise PersistenceError("Could not update application settings.") from exc

    @staticmethod
    def _to_schema(
        model: AppSettingsModel,
    ) -> AppSettingsSchema:
        return AppSettingsSchema(
            bot_enabled=model.bot_enabled,
            backup_enabled=(model.backup_enabled),
            backup_directory=Path(model.backup_directory),
            compression_format=(model.compression_format),
            compression_level=(model.compression_level),
            retention_enabled=(model.retention_enabled),
            retention_keep_last=(model.retention_keep_last),
            proxy_enabled=(model.proxy_enabled),
            proxy_url=model.proxy_url,
        )
