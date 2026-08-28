from __future__ import annotations

from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CompressionFormat(StrEnum):
    ZIP = "zip"


class ScheduleUnit(StrEnum):
    MINUTES = "minutes"
    HOURS = "hours"
    DAYS = "days"


class DatabaseType(StrEnum):
    SQLITE = "sqlite"


class ProxyConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool = False
    url: str = ""

    @field_validator("url")
    @classmethod
    def validate_url(cls, value: str) -> str:
        return value.strip()


class TelegramConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    proxy: ProxyConfig = Field(
        default_factory=ProxyConfig,
    )


class BotConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    token: str = ""
    enabled: bool = True

    @field_validator("token")
    @classmethod
    def validate_token(cls, value: str) -> str:
        return value.strip()


class CompressionConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    format: CompressionFormat = CompressionFormat.ZIP

    level: int = Field(
        default=6,
        ge=0,
        le=9,
    )


class RetentionConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool = True

    keep_last: int = Field(
        default=10,
        ge=1,
    )


class BackupConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool = True

    directory: Path = Path("./backups")

    compression: CompressionConfig = Field(
        default_factory=CompressionConfig,
    )

    retention: RetentionConfig = Field(
        default_factory=RetentionConfig,
    )

    @field_validator("directory")
    @classmethod
    def validate_directory(
        cls,
        value: Path,
    ) -> Path:
        return value.expanduser()


class DatabaseConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: DatabaseType = DatabaseType.SQLITE

    path: Path

    @field_validator("path")
    @classmethod
    def validate_path(
        cls,
        value: Path,
    ) -> Path:
        return value.expanduser()


class MediaConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool = True

    path: Path

    @field_validator("path")
    @classmethod
    def validate_path(
        cls,
        value: Path,
    ) -> Path:
        return value.expanduser()


class ScheduleConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool = True

    interval: int = Field(
        default=6,
        ge=1,
    )

    unit: ScheduleUnit = ScheduleUnit.HOURS


class ProjectConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(
        min_length=1,
        max_length=100,
    )

    name: str = Field(
        min_length=1,
        max_length=200,
    )

    enabled: bool = True

    database: DatabaseConfig

    media: MediaConfig

    schedule: ScheduleConfig = Field(
        default_factory=ScheduleConfig,
    )

    @field_validator("name")
    @classmethod
    def validate_name(
        cls,
        value: str,
    ) -> str:
        normalized = value.strip()

        if not normalized:
            raise ValueError("Project name cannot be empty.")

        return normalized


class AppConfig(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
    )

    version: int = Field(
        default=1,
        ge=1,
    )

    bot: BotConfig = Field(
        default_factory=BotConfig,
    )

    telegram: TelegramConfig = Field(
        default_factory=TelegramConfig,
    )

    admins: list[int] = Field(
        default_factory=list,
    )

    backup: BackupConfig = Field(
        default_factory=BackupConfig,
    )

    projects: list[ProjectConfig] = Field(
        default_factory=list,
    )

    @field_validator("admins")
    @classmethod
    def validate_admins(
        cls,
        value: list[int],
    ) -> list[int]:
        return list(dict.fromkeys(value))

    @field_validator("projects")
    @classmethod
    def validate_projects(
        cls,
        value: list[ProjectConfig],
    ) -> list[ProjectConfig]:
        project_ids = [project.id for project in value]

        if len(project_ids) != len(set(project_ids)):
            raise ValueError("Project IDs must be unique.")

        project_names = [project.name.casefold() for project in value]

        if len(project_names) != len(set(project_names)):
            raise ValueError("Project names must be unique.")

        return value
