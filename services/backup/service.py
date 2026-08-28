from __future__ import annotations

import tempfile
from datetime import datetime, timezone
from pathlib import Path

from config.models import (
    DatabaseType,
    ProjectConfig,
)
from services.backup.archive import ArchiveService
from services.backup.checksum import ChecksumService
from services.backup.database import SQLiteBackup
from services.backup.exceptions import BackupError
from services.backup.media import MediaCollector
from services.backup.models import (
    BackupResult,
    BackupStatus,
)
from services.backup.retention import RetentionService


class BackupService:
    """
    High-level backup orchestrator.

    This service is independent from Telegram,
    scheduler, configuration persistence,
    and UI layers.
    """

    def __init__(
        self,
        backup_directory: Path,
        compression_level: int = 6,
        retention_enabled: bool = True,
        keep_last: int = 10,
    ) -> None:
        self._backup_directory = backup_directory.expanduser()

        self._database_backup = SQLiteBackup()

        self._media_collector = MediaCollector()

        self._archive_service = ArchiveService(
            compression_level=compression_level,
        )

        self._checksum_service = ChecksumService()

        self._retention_service = RetentionService()

        self._retention_enabled = retention_enabled

        self._keep_last = keep_last

    def backup_project(
        self,
        project: ProjectConfig,
    ) -> BackupResult:
        started_at = datetime.now(
            timezone.utc,
        )

        self._validate_project(project)

        project_directory = self._backup_directory / project.id

        project_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        timestamp = started_at.strftime(
            "%Y%m%d_%H%M%S",
        )

        archive_path = project_directory / (f"{project.id}_" f"{timestamp}.zip")

        try:
            with tempfile.TemporaryDirectory(
                prefix="django-backup-",
            ) as temporary_directory:

                temporary_path = Path(
                    temporary_directory,
                )

                database_backup_path = temporary_path / project.database.path.name

                database_result = self._database_backup.create(
                    source_path=(project.database.path),
                    destination_path=(database_backup_path),
                )

                media_result = None

                if project.media.enabled:
                    media_result = self._media_collector.collect(
                        project.media.path,
                    )

                archive_result = self._archive_service.create(
                    archive_path=archive_path,
                    database=database_result,
                    media=media_result,
                )

            checksum_result = self._checksum_service.calculate(
                archive_result.archive_path,
            )

            if self._retention_enabled:
                self._retention_service.cleanup(
                    project_directory=(project_directory),
                    keep_last=self._keep_last,
                )

            finished_at = datetime.now(
                timezone.utc,
            )

            return BackupResult(
                project_id=project.id,
                project_name=project.name,
                status=BackupStatus.SUCCESS,
                archive_path=(archive_result.archive_path),
                started_at=started_at,
                finished_at=finished_at,
                database_size_bytes=(database_result.size_bytes),
                media_size_bytes=(
                    media_result.total_size_bytes if media_result is not None else 0
                ),
                archive_size_bytes=(archive_result.size_bytes),
                media_file_count=(
                    media_result.file_count if media_result is not None else 0
                ),
                checksum=checksum_result,
            )

        except BackupError:
            self._remove_partial_archive(
                archive_path,
            )
            raise

        except Exception:
            self._remove_partial_archive(
                archive_path,
            )
            raise

    @staticmethod
    def _validate_project(
        project: ProjectConfig,
    ) -> None:
        if not project.enabled:
            raise BackupError(f"Project is disabled: " f"{project.name}")

        if project.database.type != DatabaseType.SQLITE:
            raise BackupError("Only SQLite databases are " "currently supported.")

        if not project.database.path.exists():
            raise BackupError("Database does not exist: " f"{project.database.path}")

        if not project.database.path.is_file():
            raise BackupError(
                "Database path is not a file: " f"{project.database.path}"
            )

        if project.media.enabled:
            if not project.media.path.exists():
                raise BackupError(
                    "Media directory does not " "exist: " f"{project.media.path}"
                )

            if not project.media.path.is_dir():
                raise BackupError(
                    "Media path is not a directory: " f"{project.media.path}"
                )

    @staticmethod
    def _remove_partial_archive(
        archive_path: Path,
    ) -> None:
        try:
            if archive_path.exists():
                archive_path.unlink()
        except OSError:
            pass
