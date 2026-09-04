from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from django_assistant_bot.database.models.enums import (
    BackupStatus,
)


@dataclass(
    frozen=True,
    slots=True,
)
class DatabaseBackupResult:
    """
    Result of a database backup operation.
    """

    source_path: Path

    backup_path: Path

    size_bytes: int


@dataclass(
    frozen=True,
    slots=True,
)
class MediaBackupResult:
    """
    Result of scanning a project's media directory.
    """

    source_path: Path

    file_count: int

    total_size_bytes: int


@dataclass(
    frozen=True,
    slots=True,
)
class ArchiveResult:
    """
    Result of creating the final backup archive.
    """

    archive_path: Path

    size_bytes: int


@dataclass(
    frozen=True,
    slots=True,
)
class ChecksumResult:
    """
    Cryptographic checksum information.
    """

    algorithm: str

    value: str


@dataclass(
    frozen=True,
    slots=True,
)
class BackupRetentionSummary:
    """
    Retention information attached to a successful backup.

    None on BackupResult means retention was disabled.

    cleanup_failed=True means backup itself succeeded but
    retention cleanup failed and no reliable cleanup counts
    are available.
    """

    keep_last: int

    successful_before: int | None = None

    successful_after: int | None = None

    removed_count: int = 0

    failed_archive_count: int = 0

    cleanup_failed: bool = False


@dataclass(
    frozen=True,
    slots=True,
)
class BackupResult:
    """
    Final result of a successful project backup.
    """

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

    retention: BackupRetentionSummary | None = None

    @property
    def duration_seconds(self) -> float:
        """
        Return backup duration in seconds.
        """

        return (self.finished_at - self.started_at).total_seconds()

    @property
    def duration_text(self) -> str:
        """
        Return a human-readable backup duration.
        """

        seconds = self.duration_seconds

        if seconds < 60:
            return f"{seconds:.1f}s"

        minutes = int(seconds // 60)

        remaining_seconds = int(seconds % 60)

        return f"{minutes}m " f"{remaining_seconds}s"


__all__ = [
    "ArchiveResult",
    "BackupResult",
    "BackupRetentionSummary",
    "ChecksumResult",
    "DatabaseBackupResult",
    "MediaBackupResult",
]
