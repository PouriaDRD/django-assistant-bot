from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from pathlib import Path


class BackupStatus(StrEnum):
    SUCCESS = "success"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class DatabaseBackupResult:
    source_path: Path
    backup_path: Path
    size_bytes: int


@dataclass(frozen=True, slots=True)
class MediaBackupResult:
    source_path: Path
    file_count: int
    total_size_bytes: int


@dataclass(frozen=True, slots=True)
class ArchiveResult:
    archive_path: Path
    size_bytes: int


@dataclass(frozen=True, slots=True)
class ChecksumResult:
    algorithm: str
    value: str


@dataclass(frozen=True, slots=True)
class BackupResult:
    project_id: str
    project_name: str

    status: BackupStatus

    archive_path: Path

    started_at: datetime
    finished_at: datetime

    database_size_bytes: int
    media_size_bytes: int
    archive_size_bytes: int

    media_file_count: int

    checksum: ChecksumResult

    @property
    def duration_seconds(self) -> float:
        return (self.finished_at - self.started_at).total_seconds()

    @property
    def duration_text(self) -> str:
        seconds = self.duration_seconds

        if seconds < 60:
            return f"{seconds:.1f}s"

        minutes = int(seconds // 60)
        remaining_seconds = int(seconds % 60)

        return f"{minutes}m " f"{remaining_seconds}s"
