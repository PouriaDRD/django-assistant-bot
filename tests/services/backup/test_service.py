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
from django_assistant_bot.services.backup import BackupService
from django_assistant_bot.services.backup.exceptions import (
    BackupError,
)


def create_sqlite_database(
    path: Path,
) -> None:
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


def test_backup_project(
    tmp_path: Path,
) -> None:
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
        retention_enabled=True,
        keep_last=10,
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


def test_disabled_project_cannot_be_backed_up(
    tmp_path: Path,
) -> None:
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


def test_missing_media_directory_fails(
    tmp_path: Path,
) -> None:
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


def test_invalid_compression_level_fails(
    tmp_path: Path,
) -> None:
    with pytest.raises(
        ValueError,
    ):
        BackupService(
            backup_directory=tmp_path,
            compression_level=10,
        )


def test_invalid_keep_last_fails(
    tmp_path: Path,
) -> None:
    with pytest.raises(
        ValueError,
    ):
        BackupService(
            backup_directory=tmp_path,
            keep_last=0,
        )
