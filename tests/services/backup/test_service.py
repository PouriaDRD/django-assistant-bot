from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from django_assistant_bot.database.models.enums import (
    BackupStatus,
    DatabaseType,
    ScheduleUnit,
)
from django_assistant_bot.schemas.project import (
    DatabaseSchema,
    MediaSchema,
    ProjectSchema,
    ScheduleSchema,
)
from django_assistant_bot.services.backup import (
    BackupService,
)
from django_assistant_bot.services.backup.exceptions import (
    BackupError,
)

# =========================================================
# HELPERS
# =========================================================


def create_sqlite_database(
    path: Path,
) -> None:
    """
    Create a small valid SQLite database for backup tests.
    """

    connection = sqlite3.connect(
        path,
    )

    try:
        connection.execute("""
            CREATE TABLE test (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL
            )
            """)

        connection.execute("""
            INSERT INTO test (name)
            VALUES ('backup-test')
            """)

        connection.commit()

    finally:
        connection.close()


def build_project(
    *,
    database_path: Path,
    media_path: Path,
    enabled: bool = True,
    media_enabled: bool = True,
) -> ProjectSchema:
    """
    Build a project schema for backup tests.
    """

    return ProjectSchema(
        id="test-project-id",
        name="test-project",
        enabled=enabled,
        database=DatabaseSchema(
            type=DatabaseType.SQLITE,
            path=database_path,
        ),
        media=MediaSchema(
            enabled=media_enabled,
            path=media_path,
        ),
        schedule=ScheduleSchema(
            enabled=True,
            interval=1,
            unit=ScheduleUnit.HOURS,
        ),
    )


# =========================================================
# SUCCESS
# =========================================================


def test_backup_project(
    tmp_path: Path,
) -> None:
    """
    A complete project backup should create a valid archive.
    """

    database_path = tmp_path / "db.sqlite3"

    media_path = tmp_path / "media"

    backups_path = tmp_path / "backups"

    create_sqlite_database(
        database_path,
    )

    media_path.mkdir()

    (media_path / "test.txt").write_text(
        "hello backup",
        encoding="utf-8",
    )

    project = build_project(
        database_path=database_path,
        media_path=media_path,
    )

    service = BackupService(
        backup_directory=backups_path,
        compression_level=6,
    )

    result = service.backup_project(
        project,
    )

    assert result.status is BackupStatus.SUCCESS

    assert result.archive_path.exists()

    assert result.archive_path.is_file()

    assert result.database_size_bytes > 0

    assert result.media_size_bytes > 0

    assert result.archive_size_bytes > 0

    assert result.media_file_count == 1

    assert result.checksum.value


def test_backup_without_media(
    tmp_path: Path,
) -> None:
    """
    Backup should succeed when media backup is disabled.
    """

    database_path = tmp_path / "db.sqlite3"

    create_sqlite_database(
        database_path,
    )

    project = build_project(
        database_path=database_path,
        media_path=(tmp_path / "missing-media"),
        media_enabled=False,
    )

    service = BackupService(
        backup_directory=(tmp_path / "backups"),
    )

    result = service.backup_project(
        project,
    )

    assert result.status is BackupStatus.SUCCESS

    assert result.media_size_bytes == 0

    assert result.media_file_count == 0

    assert result.archive_path.exists()


# =========================================================
# PROJECT VALIDATION
# =========================================================


def test_disabled_project_cannot_be_backed_up(
    tmp_path: Path,
) -> None:
    """
    Disabled projects must not be backed up.
    """

    database_path = tmp_path / "db.sqlite3"

    media_path = tmp_path / "media"

    create_sqlite_database(
        database_path,
    )

    media_path.mkdir()

    project = build_project(
        database_path=database_path,
        media_path=media_path,
        enabled=False,
    )

    service = BackupService(
        backup_directory=(tmp_path / "backups"),
    )

    with pytest.raises(
        BackupError,
        match="disabled",
    ):
        service.backup_project(
            project,
        )


def test_missing_database_fails(
    tmp_path: Path,
) -> None:
    """
    Missing SQLite database must fail before backup starts.
    """

    media_path = tmp_path / "media"

    media_path.mkdir()

    project = build_project(
        database_path=(tmp_path / "missing.sqlite3"),
        media_path=media_path,
    )

    service = BackupService(
        backup_directory=(tmp_path / "backups"),
    )

    with pytest.raises(
        BackupError,
        match="Database does not exist",
    ):
        service.backup_project(
            project,
        )


def test_database_path_must_be_file(
    tmp_path: Path,
) -> None:
    """
    Database path must point to a file.
    """

    database_path = tmp_path / "database-directory"

    database_path.mkdir()

    media_path = tmp_path / "media"

    media_path.mkdir()

    project = build_project(
        database_path=database_path,
        media_path=media_path,
    )

    service = BackupService(
        backup_directory=(tmp_path / "backups"),
    )

    with pytest.raises(
        BackupError,
        match="Database path is not a file",
    ):
        service.backup_project(
            project,
        )


def test_missing_media_directory_fails(
    tmp_path: Path,
) -> None:
    """
    Enabled media backup requires an existing directory.
    """

    database_path = tmp_path / "db.sqlite3"

    create_sqlite_database(
        database_path,
    )

    project = build_project(
        database_path=database_path,
        media_path=(tmp_path / "missing-media"),
    )

    service = BackupService(
        backup_directory=(tmp_path / "backups"),
    )

    with pytest.raises(
        BackupError,
        match="Media directory does not exist",
    ):
        service.backup_project(
            project,
        )


def test_media_path_must_be_directory(
    tmp_path: Path,
) -> None:
    """
    Enabled media path must point to a directory.
    """

    database_path = tmp_path / "db.sqlite3"

    create_sqlite_database(
        database_path,
    )

    media_path = tmp_path / "media.txt"

    media_path.write_text(
        "not a directory",
        encoding="utf-8",
    )

    project = build_project(
        database_path=database_path,
        media_path=media_path,
    )

    service = BackupService(
        backup_directory=(tmp_path / "backups"),
    )

    with pytest.raises(
        BackupError,
        match="Media path is not a directory",
    ):
        service.backup_project(
            project,
        )


# =========================================================
# CONFIGURATION VALIDATION
# =========================================================


@pytest.mark.parametrize(
    "compression_level",
    [
        -1,
        10,
    ],
)
def test_invalid_compression_level_fails(
    tmp_path: Path,
    compression_level: int,
) -> None:
    """
    Compression level must remain inside ZIP range 0..9.
    """

    with pytest.raises(
        ValueError,
        match="Compression level",
    ):
        BackupService(
            backup_directory=tmp_path,
            compression_level=(compression_level),
        )
