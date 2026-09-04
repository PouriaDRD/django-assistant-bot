from __future__ import annotations

from pathlib import Path

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)

from django_assistant_bot.database.models.enums import (
    CompressionFormat,
)


class AppSettingsSchema(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )

    bot_enabled: bool = True

    backup_enabled: bool = True

    backup_directory: Path = Path("data/backups")

    compression_format: CompressionFormat = CompressionFormat.ZIP

    compression_level: int = Field(
        default=6,
        ge=0,
        le=9,
    )

    retention_enabled: bool = True

    retention_keep_last: int = Field(
        default=10,
        ge=1,
    )

    proxy_enabled: bool = False

    proxy_url: str = ""

    @field_validator("backup_directory")
    @classmethod
    def normalize_backup_directory(
        cls,
        value: Path,
    ) -> Path:
        """
        Normalize configured backup directory.
        """

        return value.expanduser()

    @field_validator("proxy_url")
    @classmethod
    def normalize_proxy_url(
        cls,
        value: str,
    ) -> str:
        """
        Normalize proxy URL.
        """

        return value.strip()


class AppSettingsUpdateSchema(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )

    bot_enabled: bool | None = None

    backup_enabled: bool | None = None

    backup_directory: Path | None = None

    compression_format: CompressionFormat | None = None

    compression_level: int | None = Field(
        default=None,
        ge=0,
        le=9,
    )

    retention_enabled: bool | None = None

    retention_keep_last: int | None = Field(
        default=None,
        ge=1,
    )

    proxy_enabled: bool | None = None

    proxy_url: str | None = None


__all__ = [
    "AppSettingsSchema",
    "AppSettingsUpdateSchema",
]
