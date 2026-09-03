from __future__ import annotations

from datetime import datetime
from pathlib import Path

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)

from django_assistant_bot.database.models.enums import (
    BackupStatus,
)


class BackupHistoryCreateSchema(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )

    project_id: str

    status: BackupStatus

    archive_path: Path | None = None

    database_size_bytes: int = Field(
        default=0,
        ge=0,
    )

    media_size_bytes: int = Field(
        default=0,
        ge=0,
    )

    archive_size_bytes: int = Field(
        default=0,
        ge=0,
    )

    media_file_count: int = Field(
        default=0,
        ge=0,
    )

    checksum_algorithm: str | None = None

    checksum_value: str | None = None

    error_message: str | None = None

    started_at: datetime

    finished_at: datetime | None = None


class BackupHistorySchema(BackupHistoryCreateSchema):
    id: str
