from __future__ import annotations

from pathlib import Path

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)

from django_assistant_bot.database.models.enums import (
    DatabaseType,
    ScheduleUnit,
)


class DatabaseSchema(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )

    type: DatabaseType = DatabaseType.SQLITE
    path: Path

    @field_validator("path")
    @classmethod
    def normalize_path(
        cls,
        value: Path,
    ) -> Path:
        return value.expanduser()


class MediaSchema(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )

    enabled: bool = True
    path: Path

    @field_validator("path")
    @classmethod
    def normalize_path(
        cls,
        value: Path,
    ) -> Path:
        return value.expanduser()


class ScheduleSchema(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )

    enabled: bool = True

    interval: int = Field(
        default=6,
        ge=1,
    )

    unit: ScheduleUnit = ScheduleUnit.HOURS


class ProjectCreateSchema(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )

    name: str = Field(
        min_length=1,
        max_length=200,
    )

    database: DatabaseSchema

    media: MediaSchema

    schedule: ScheduleSchema = Field(
        default_factory=ScheduleSchema,
    )

    @field_validator("name")
    @classmethod
    def normalize_name(
        cls,
        value: str,
    ) -> str:
        normalized = value.strip()

        if not normalized:
            raise ValueError("Project name cannot be empty.")

        return normalized


class ProjectUpdateSchema(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )

    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=200,
    )

    enabled: bool | None = None

    database: DatabaseSchema | None = None

    media: MediaSchema | None = None

    schedule: ScheduleSchema | None = None

    @field_validator("name")
    @classmethod
    def normalize_name(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        normalized = value.strip()

        if not normalized:
            raise ValueError("Project name cannot be empty.")

        return normalized


class ProjectSchema(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )

    id: str
    name: str
    enabled: bool

    database: DatabaseSchema

    media: MediaSchema

    schedule: ScheduleSchema
