from __future__ import annotations

import tempfile
from datetime import (
    datetime,
    timezone,
)
from pathlib import Path

from django_assistant_bot.database.models.enums import (
    BackupStatus,
    DatabaseType,
)
from django_assistant_bot.schemas.project import (
    ProjectSchema,
)
from django_assistant_bot.services.backup.archive import (
    ArchiveService,
)
from django_assistant_bot.services.backup.checksum import (
    ChecksumService,
)
from django_assistant_bot.services.backup.database import (
    SQLiteBackup,
)
from django_assistant_bot.services.backup.exceptions import (
    BackupError,
    ProjectBackupDisabledError,
)
from django_assistant_bot.services.backup.media import (
    MediaCollector,
)
from django_assistant_bot.services.backup.models import (
    BackupResult,
)


class BackupService:
    """
    High-level backup executor.

    Responsibilities:
    - validate project backup requirements
    - create a safe database backup
    - collect optional media files
    - create the final archive
    - calculate archive checksum

    Retention intentionally does not belong here.

    Retention is an application-level concern because it
    must coordinate both filesystem archives and persisted
    backup history.

    This service is intentionally independent from:
    - Telegram
    - scheduler
    - SQLAlchemy
    - configuration persistence
    - retention persistence
    - UI layers
    """

    def __init__(
        self,
        backup_directory: Path,
        compression_level: int = 6,
    ) -> None:
        if not 0 <= compression_level <= 9:
            raise ValueError(("Compression level must be " "between 0 and 9."))

        self._backup_directory = backup_directory.expanduser()

        self._database_backup = SQLiteBackup()

        self._media_collector = MediaCollector()

        self._archive_service = ArchiveService(
            compression_level=(compression_level),
        )

        self._checksum_service = ChecksumService()

    def backup_project(
        self,
        project: ProjectSchema,
    ) -> BackupResult:
        """
        Create a complete backup for a project.

        Raises:
            BackupError:
                If project validation or one of the
                backup operations fails.
        """

        started_at = datetime.now(
            timezone.utc,
        )

        self._validate_project(
            project,
        )

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
        project: ProjectSchema,
    ) -> None:
        """
        Validate project before backup execution.
        """

        if not project.enabled:
            raise ProjectBackupDisabledError(
                ("Project is disabled: " f"{project.name}")
            )

        if project.database.type is not DatabaseType.SQLITE:
            raise BackupError(("Only SQLite databases are " "currently supported."))

        database_path = project.database.path

        if not database_path.exists():
            raise BackupError(("Database does not exist: " f"{database_path}"))

        if not database_path.is_file():
            raise BackupError(("Database path is not a file: " f"{database_path}"))

        if not project.media.enabled:
            return

        media_path = project.media.path

        if not media_path.exists():
            raise BackupError(("Media directory does not exist: " f"{media_path}"))

        if not media_path.is_dir():
            raise BackupError(("Media path is not a directory: " f"{media_path}"))

    @staticmethod
    def _remove_partial_archive(
        archive_path: Path,
    ) -> None:
        """
        Remove an incomplete archive after a failed backup.

        Cleanup errors are intentionally ignored so they do
        not hide the original backup exception.
        """

        try:
            if archive_path.exists():
                archive_path.unlink()

        except OSError:
            pass
