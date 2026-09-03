from __future__ import annotations

from enum import StrEnum


class CompressionFormat(StrEnum):
    ZIP = "zip"


class ScheduleUnit(StrEnum):
    MINUTES = "minutes"
    HOURS = "hours"
    DAYS = "days"


class DatabaseType(StrEnum):
    SQLITE = "sqlite"


class BackupStatus(StrEnum):
    SUCCESS = "success"
    FAILED = "failed"
