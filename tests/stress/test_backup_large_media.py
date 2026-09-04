from __future__ import annotations

import sqlite3
import zipfile
from pathlib import (
    Path,
)

import pytest

from django_assistant_bot.database.models.enums import (
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
from django_assistant_bot.services.backup.media import (
    MediaCollector,
)

# =========================================================
# CONFIGURATION
# =========================================================


PROJECT_ID = "large-media-stress-project"

SMALL_FILE_COUNT = 1_500

SMALL_FILE_SIZE = 256

DIRECTORY_COUNT = 30

LARGE_FILE_SIZE = 12 * 1024 * 1024

DEEP_DIRECTORY_DEPTH = 8


# =========================================================
# BUILDERS
# =========================================================


def build_sqlite_database(
    database_path: Path,
) -> None:
    """
    Create a real SQLite database for backup tests.
    """

    connection = sqlite3.connect(
        database_path,
    )

    try:
        connection.execute("""
            CREATE TABLE stress_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                value TEXT NOT NULL
            );
            """)

        connection.executemany(
            """
            INSERT INTO stress_data (value)
            VALUES (?);
            """,
            [(f"value-{index}",) for index in range(100)],
        )

        connection.commit()

    finally:
        connection.close()


def build_project(
    tmp_path: Path,
    *,
    media_path: Path,
) -> ProjectSchema:
    database_path = tmp_path / "project.sqlite3"

    build_sqlite_database(
        database_path,
    )

    return ProjectSchema(
        id=PROJECT_ID,
        name="Large Media Stress Project",
        enabled=True,
        database=DatabaseSchema(
            type=DatabaseType.SQLITE,
            path=database_path,
        ),
        media=MediaSchema(
            enabled=True,
            path=media_path,
        ),
        schedule=ScheduleSchema(
            enabled=True,
            interval=1,
            unit=ScheduleUnit.HOURS,
        ),
    )


def build_service(
    tmp_path: Path,
) -> BackupService:
    return BackupService(
        backup_directory=(tmp_path / "backups"),
        compression_level=6,
    )


# =========================================================
# MANY SMALL FILES
# =========================================================


def create_many_small_files(
    media_path: Path,
) -> int:
    """
    Create many files distributed across several directories.

    Returns the expected total media size.
    """

    payload = b"x" * SMALL_FILE_SIZE

    total_size = 0

    for index in range(SMALL_FILE_COUNT):
        directory_index = index % DIRECTORY_COUNT

        directory = media_path / f"directory-{directory_index:02d}"

        directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        file_path = directory / f"file-{index:05d}.bin"

        file_path.write_bytes(payload)

        total_size += len(payload)

    return total_size


def test_backup_handles_many_small_media_files(
    tmp_path: Path,
) -> None:
    """
    Backup a project containing many small media files.

    Expected:

    - every file is counted
    - total media size is exact
    - every file appears exactly once in the ZIP
    - database backup is also present
    - archive and checksum are produced successfully
    """

    media_path = tmp_path / "media-many-files"

    media_path.mkdir(
        parents=True,
    )

    expected_media_size = create_many_small_files(
        media_path,
    )

    project = build_project(
        tmp_path,
        media_path=media_path,
    )

    service = build_service(
        tmp_path,
    )

    result = service.backup_project(
        project,
    )

    # -----------------------------------------------------
    # BACKUP RESULT
    # -----------------------------------------------------

    assert result.project_id == (PROJECT_ID)

    assert result.media_file_count == SMALL_FILE_COUNT

    assert result.media_size_bytes == expected_media_size

    assert result.archive_size_bytes > 0

    assert result.archive_path.exists()

    assert result.checksum.algorithm == "sha256"

    assert len(result.checksum.value) == 64

    # -----------------------------------------------------
    # ZIP CONTENT
    # -----------------------------------------------------

    with zipfile.ZipFile(
        result.archive_path,
        mode="r",
    ) as archive:
        names = archive.namelist()

        media_names = [name for name in names if name.startswith("media/")]

        database_names = [name for name in names if name.startswith("database/")]

        assert len(media_names) == SMALL_FILE_COUNT

        assert len(set(media_names)) == SMALL_FILE_COUNT

        assert len(database_names) == 1

        assert archive.testzip() is None


# =========================================================
# MEDIA COLLECTOR LARGE FILE COUNT
# =========================================================


def test_media_collector_counts_large_file_set_exactly(
    tmp_path: Path,
) -> None:
    """
    Stress MediaCollector directly with many files.

    This verifies traversal and stat accounting independently
    from ZIP compression.
    """

    media_path = tmp_path / "collector-media"

    media_path.mkdir(
        parents=True,
    )

    expected_total_size = create_many_small_files(
        media_path,
    )

    collector = MediaCollector()

    result = collector.collect(
        media_path,
    )

    assert result.file_count == SMALL_FILE_COUNT

    assert result.total_size_bytes == expected_total_size

    assert result.source_path == media_path


# =========================================================
# LARGE SINGLE FILE
# =========================================================


def test_backup_handles_large_media_file(
    tmp_path: Path,
) -> None:
    """
    Backup a reasonably large media file without requiring
    the whole file to be loaded by MediaCollector.
    """

    media_path = tmp_path / "media-large-file"

    media_path.mkdir(
        parents=True,
    )

    large_file = media_path / "large-file.bin"

    # Repeated deterministic chunk.
    chunk = b"django-assistant-bot-stress" * 1024

    remaining = LARGE_FILE_SIZE

    with large_file.open(
        "wb",
    ) as file:
        while remaining > 0:
            data = chunk[
                : min(
                    len(chunk),
                    remaining,
                )
            ]

            file.write(data)

            remaining -= len(data)

    assert large_file.stat().st_size == LARGE_FILE_SIZE

    project = build_project(
        tmp_path,
        media_path=media_path,
    )

    service = build_service(
        tmp_path,
    )

    result = service.backup_project(
        project,
    )

    assert result.media_file_count == 1

    assert result.media_size_bytes == LARGE_FILE_SIZE

    assert result.archive_path.exists()

    assert result.archive_size_bytes > 0

    # -----------------------------------------------------
    # VERIFY LARGE FILE INSIDE ARCHIVE
    # -----------------------------------------------------

    with zipfile.ZipFile(
        result.archive_path,
        mode="r",
    ) as archive:
        info = archive.getinfo("media/large-file.bin")

        assert info.file_size == LARGE_FILE_SIZE

        assert archive.testzip() is None


# =========================================================
# DEEPLY NESTED MEDIA
# =========================================================


def test_backup_preserves_nested_media_structure(
    tmp_path: Path,
) -> None:
    """
    Verify nested media paths survive the collection and ZIP
    process without being flattened or duplicated.
    """

    media_path = tmp_path / "nested-media"

    current_directory = media_path

    expected_relative_paths: list[Path] = []

    for depth in range(DEEP_DIRECTORY_DEPTH):
        current_directory = current_directory / f"level-{depth}"

        current_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        file_path = current_directory / f"file-{depth}.txt"

        file_path.write_text(
            ("nested-media-content-" f"{depth}"),
            encoding="utf-8",
        )

        expected_relative_paths.append(
            file_path.relative_to(
                media_path,
            )
        )

    project = build_project(
        tmp_path,
        media_path=media_path,
    )

    service = build_service(
        tmp_path,
    )

    result = service.backup_project(
        project,
    )

    assert result.media_file_count == DEEP_DIRECTORY_DEPTH

    with zipfile.ZipFile(
        result.archive_path,
        mode="r",
    ) as archive:
        archive_names = set(archive.namelist())

        expected_archive_names = {
            (Path("media") / relative_path).as_posix()
            for relative_path in expected_relative_paths
        }

        assert expected_archive_names <= archive_names

        assert archive.testzip() is None


# =========================================================
# MIXED FILE SIZES
# =========================================================


@pytest.mark.parametrize(
    "file_size",
    [
        0,
        1,
        64,
        1024,
        64 * 1024,
        512 * 1024,
    ],
)
def test_media_collector_handles_mixed_file_sizes(
    tmp_path: Path,
    file_size: int,
) -> None:
    """
    Ensure media accounting remains correct across empty,
    tiny and moderately sized files.
    """

    media_path = tmp_path / f"media-size-{file_size}"

    media_path.mkdir(
        parents=True,
    )

    file_path = media_path / "file.bin"

    file_path.write_bytes(b"x" * file_size)

    collector = MediaCollector()

    result = collector.collect(
        media_path,
    )

    assert result.file_count == 1

    assert result.total_size_bytes == file_size
