from __future__ import annotations

import sqlite3
from pathlib import Path

from django_assistant_bot.services.backup.exceptions import (
    BackupValidationError,
    DatabaseBackupError,
)
from django_assistant_bot.services.backup.models import DatabaseBackupResult


class SQLiteBackup:
    """
    Creates a consistent SQLite database backup.

    The native SQLite backup API is used instead of copying
    the database file directly.

    Connections are explicitly closed to avoid file-locking
    issues, especially on Windows.
    """

    def create(
        self,
        source_path: Path,
        destination_path: Path,
    ) -> DatabaseBackupResult:
        self._validate_source(source_path)

        destination_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        source_connection: sqlite3.Connection | None = None
        destination_connection: sqlite3.Connection | None = None

        try:
            source_connection = sqlite3.connect(
                source_path,
            )

            destination_connection = sqlite3.connect(
                destination_path,
            )

            source_connection.backup(
                destination_connection,
            )

            destination_connection.commit()

        except sqlite3.Error as exc:
            self._cleanup_destination(
                destination_path,
            )

            raise DatabaseBackupError(
                "Failed to create SQLite backup: " f"{source_path}"
            ) from exc

        finally:
            if source_connection is not None:
                source_connection.close()

            if destination_connection is not None:
                destination_connection.close()

        if not destination_path.exists():
            raise DatabaseBackupError(
                "SQLite backup destination was not created: " f"{destination_path}"
            )

        try:
            size_bytes = destination_path.stat().st_size
        except OSError as exc:
            self._cleanup_destination(
                destination_path,
            )

            raise DatabaseBackupError(
                "Could not inspect SQLite backup: " f"{destination_path}"
            ) from exc

        return DatabaseBackupResult(
            source_path=source_path,
            backup_path=destination_path,
            size_bytes=size_bytes,
        )

    @staticmethod
    def _validate_source(
        source_path: Path,
    ) -> None:
        if not source_path.exists():
            raise BackupValidationError(
                "Database file does not exist: " f"{source_path}"
            )

        if not source_path.is_file():
            raise BackupValidationError(
                "Database path is not a file: " f"{source_path}"
            )

    @staticmethod
    def _cleanup_destination(
        destination_path: Path,
    ) -> None:
        try:
            destination_path.unlink(
                missing_ok=True,
            )
        except OSError:
            pass
