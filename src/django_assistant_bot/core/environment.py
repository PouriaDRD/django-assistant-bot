from __future__ import annotations

from enum import StrEnum

from pydantic import (
    Field,
    SecretStr,
    ValidationError,
    field_validator,
)
from pydantic_settings import (
    BaseSettings,
    SettingsConfigDict,
)

from django_assistant_bot.core.exceptions import (
    EnvironmentValidationError,
)
from django_assistant_bot.core.paths import (
    ENV_FILE,
)


class AppEnvironment(StrEnum):
    DEVELOPMENT = "development"

    PRODUCTION = "production"

    TESTING = "testing"


class LogLevel(StrEnum):
    DEBUG = "DEBUG"

    INFO = "INFO"

    WARNING = "WARNING"

    ERROR = "ERROR"

    CRITICAL = "CRITICAL"


class EnvironmentSettings(BaseSettings):
    """
    Strongly typed bootstrap configuration.

    Only secrets and settings required before the application
    database is available belong here.

    Runtime settings are stored in SQLite.
    """

    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        env_prefix="DAB_",
        case_sensitive=False,
        extra="ignore",
        frozen=True,
        validate_default=True,
    )

    environment: AppEnvironment = AppEnvironment.DEVELOPMENT

    telegram_bot_token: SecretStr = Field(
        default=SecretStr(""),
    )

    log_level: LogLevel = LogLevel.INFO

    bootstrap_admin_ids: list[int] = Field(
        default_factory=list,
    )

    @field_validator(
        "telegram_bot_token",
    )
    @classmethod
    def validate_telegram_bot_token(
        cls,
        value: SecretStr,
    ) -> SecretStr:
        """
        Validate Telegram bot token.
        """

        token = value.get_secret_value().strip()

        if not token:
            raise ValueError("Telegram bot token cannot be empty.")

        if ":" not in token:
            raise ValueError("Telegram bot token has an invalid format.")

        return SecretStr(token)

    @field_validator(
        "bootstrap_admin_ids",
    )
    @classmethod
    def validate_bootstrap_admin_ids(
        cls,
        value: list[int],
    ) -> list[int]:
        """
        Normalize and validate bootstrap administrators.
        """

        unique_ids = list(dict.fromkeys(value))

        for telegram_user_id in unique_ids:
            if telegram_user_id <= 0:
                raise ValueError(("Bootstrap admin IDs " "must be positive."))

        return unique_ids

    @property
    def is_development(
        self,
    ) -> bool:
        return self.environment is AppEnvironment.DEVELOPMENT

    @property
    def is_production(
        self,
    ) -> bool:
        return self.environment is AppEnvironment.PRODUCTION

    @property
    def is_testing(
        self,
    ) -> bool:
        return self.environment is AppEnvironment.TESTING


class EnvironmentManager:
    """
    Loads and owns immutable environment configuration.
    """

    def __init__(
        self,
    ) -> None:
        self._settings: EnvironmentSettings | None = None

    @property
    def settings(
        self,
    ) -> EnvironmentSettings:
        if self._settings is None:
            raise EnvironmentValidationError(
                ("Environment configuration " "has not been loaded.")
            )

        return self._settings

    def load(
        self,
    ) -> EnvironmentSettings:
        try:
            settings = EnvironmentSettings()

        except ValidationError as exc:
            raise EnvironmentValidationError(
                ("Invalid environment " "configuration.")
            ) from exc

        self._settings = settings

        return settings

    def reload(
        self,
    ) -> EnvironmentSettings:
        return self.load()


__all__ = [
    "AppEnvironment",
    "EnvironmentManager",
    "EnvironmentSettings",
    "LogLevel",
]
