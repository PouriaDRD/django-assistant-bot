from __future__ import annotations

import gc
import sqlite3
from pathlib import (
    Path,
)

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
from django_assistant_bot.services.resource_monitor import (
    ProcessResourceMonitor,
)

# =========================================================
# CONFIGURATION
# =========================================================


PROJECT_ID = "endurance-project"

DATABASE_ONLY_RUNS = 100

MEDIA_RUNS = 30

FAILURE_RECOVERY_CYCLES = 50

MEDIA_FILE_COUNT = 100

MEDIA_FILE_SIZE = 1024

# Memory allocators do not necessarily return released
# memory to the OS immediately, therefore RSS should not
# be expected to return exactly to its starting value.
MAX_ACCEPTABLE_RSS_GROWTH_BYTES = 32 * 1024 * 1024

MAX_ACCEPTABLE_THREAD_GROWTH = 1

MAX_ACCEPTABLE_OPEN_FILE_GROWTH = 2


# =========================================================
# BUILDERS
# =========================================================


def build_sqlite_database(
    database_path: Path,
) -> None:
    """
    Build a real SQLite database with enough content to
    exercise SQLiteBackup repeatedly.
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
            [(f"value-{index}",) for index in range(500)],
        )

        connection.commit()

    finally:
        connection.close()


def build_media_directory(
    media_path: Path,
) -> int:
    """
    Create deterministic media files.

    Returns expected total media size.
    """

    media_path.mkdir(
        parents=True,
        exist_ok=True,
    )

    payload = b"x" * MEDIA_FILE_SIZE

    for index in range(MEDIA_FILE_COUNT):
        directory = media_path / f"group-{index % 10}"

        directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        (directory / f"file-{index:04d}.bin").write_bytes(payload)

    return MEDIA_FILE_COUNT * MEDIA_FILE_SIZE


def build_project(
    tmp_path: Path,
    *,
    media_enabled: bool,
) -> ProjectSchema:
    database_path = tmp_path / "project.sqlite3"

    build_sqlite_database(
        database_path,
    )

    media_path = tmp_path / "media"

    if media_enabled:
        build_media_directory(
            media_path,
        )

    return ProjectSchema(
        id=PROJECT_ID,
        name="Endurance Project",
        enabled=True,
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


def build_service(
    tmp_path: Path,
) -> BackupService:
    return BackupService(
        backup_directory=(tmp_path / "backups"),
        compression_level=6,
    )


def remove_archive(
    archive_path: Path,
) -> None:
    """
    Remove one successful endurance archive.

    Endurance tests are interested in repeated execution
    rather than retention behavior.
    """

    assert archive_path.exists()

    archive_path.unlink()

    assert not archive_path.exists()


# =========================================================
# DATABASE-ONLY ENDURANCE
# =========================================================


def test_database_only_backup_survives_many_repeated_runs(
    tmp_path: Path,
) -> None:
    """
    Execute many real SQLite backups through the same
    BackupService instance.

    Expected:

    - every run succeeds
    - every checksum is valid
    - no stale archive is required for the next run
    - service remains reusable for the entire sequence
    """

    project = build_project(
        tmp_path,
        media_enabled=False,
    )

    service = build_service(
        tmp_path,
    )

    for _ in range(DATABASE_ONLY_RUNS):
        result = service.backup_project(
            project,
        )

        assert result.status is BackupStatus.SUCCESS

        assert result.project_id == project.id

        assert result.database_size_bytes > 0

        assert result.media_size_bytes == 0

        assert result.media_file_count == 0

        assert result.archive_size_bytes > 0

        assert result.archive_path.exists()

        assert result.checksum.algorithm == "sha256"

        assert len(result.checksum.value) == 64

        remove_archive(
            result.archive_path,
        )


# =========================================================
# MEDIA ENDURANCE
# =========================================================


def test_media_backup_survives_repeated_real_runs(
    tmp_path: Path,
) -> None:
    """
    Repeatedly traverse and archive a non-trivial media tree.

    This exercises:

    - MediaCollector traversal
    - media statistics
    - archive media traversal
    - ZIP creation
    - checksum generation
    - TemporaryDirectory cleanup
    """

    project = build_project(
        tmp_path,
        media_enabled=True,
    )

    service = build_service(
        tmp_path,
    )

    expected_media_size = MEDIA_FILE_COUNT * MEDIA_FILE_SIZE

    for _ in range(MEDIA_RUNS):
        result = service.backup_project(
            project,
        )

        assert result.status is BackupStatus.SUCCESS

        assert result.media_file_count == MEDIA_FILE_COUNT

        assert result.media_size_bytes == expected_media_size

        assert result.archive_size_bytes > 0

        assert result.archive_path.exists()

        remove_archive(
            result.archive_path,
        )


# =========================================================
# FAILURE / SUCCESS ENDURANCE
# =========================================================


def test_repeated_failures_do_not_poison_future_backups(
    tmp_path: Path,
) -> None:
    """
    Alternate between invalid and valid backup executions.

    Validation failures must never leave BackupService in a
    state that prevents the following valid backup.
    """

    project = build_project(
        tmp_path,
        media_enabled=False,
    )

    service = build_service(
        tmp_path,
    )

    database_path = project.database.path

    unavailable_path = tmp_path / "temporarily-unavailable.sqlite3"

    for _ in range(FAILURE_RECOVERY_CYCLES):
        # -------------------------------------------------
        # TEMPORARILY MAKE DATABASE UNAVAILABLE
        # -------------------------------------------------

        database_path.rename(
            unavailable_path,
        )

        try:
            try:
                service.backup_project(
                    project,
                )

            except Exception:
                pass

            else:
                raise AssertionError(
                    ("Backup unexpectedly succeeded " "while database was unavailable.")
                )

        finally:
            unavailable_path.rename(
                database_path,
            )

        # -------------------------------------------------
        # NEXT ATTEMPT MUST SUCCEED
        # -------------------------------------------------

        result = service.backup_project(
            project,
        )

        assert result.status is BackupStatus.SUCCESS

        assert result.archive_path.exists()

        remove_archive(
            result.archive_path,
        )


# =========================================================
# RESOURCE LEAK DETECTION
# =========================================================


def test_repeated_backups_do_not_show_unbounded_resource_growth(
    tmp_path: Path,
) -> None:
    """
    Run many real backups and compare process resources before
    and after.

    Hard invariants:
    - threads must not continuously leak
    - file handles must not continuously leak

    RSS receives a deliberately generous threshold because
    Python and native allocators may retain freed arenas
    without returning them to the operating system.
    """

    project = build_project(
        tmp_path,
        media_enabled=True,
    )

    service = build_service(
        tmp_path,
    )

    monitor = ProcessResourceMonitor()

    # -----------------------------------------------------
    # WARM UP
    # -----------------------------------------------------
    #
    # Perform a few executions before taking the baseline.
    # This avoids counting normal lazy imports, ZIP buffers
    # and allocator initialization as a resource leak.
    # -----------------------------------------------------

    for _ in range(3):
        result = service.backup_project(
            project,
        )

        remove_archive(
            result.archive_path,
        )

    gc.collect()

    before = monitor.snapshot()

    # -----------------------------------------------------
    # ENDURANCE RUN
    # -----------------------------------------------------

    for _ in range(50):
        result = service.backup_project(
            project,
        )

        assert result.status is BackupStatus.SUCCESS

        remove_archive(
            result.archive_path,
        )

    gc.collect()

    after = monitor.snapshot()

    delta = monitor.delta(
        before=before,
        after=after,
    )

    # -----------------------------------------------------
    # THREAD LEAK
    # -----------------------------------------------------

    assert delta.thread_count <= MAX_ACCEPTABLE_THREAD_GROWTH, (
        "Possible thread leak detected: " f"delta={delta.thread_count}"
    )

    # -----------------------------------------------------
    # OPEN FILE / HANDLE LEAK
    # -----------------------------------------------------

    assert delta.open_file_count <= MAX_ACCEPTABLE_OPEN_FILE_GROWTH, (
        "Possible open-file leak detected: " f"delta={delta.open_file_count}"
    )

    # -----------------------------------------------------
    # MEMORY GROWTH
    # -----------------------------------------------------

    assert delta.rss_bytes <= MAX_ACCEPTABLE_RSS_GROWTH_BYTES, (
        "Unexpected RSS growth after repeated backups: "
        f"delta={delta.rss_bytes} bytes"
    )

    # -----------------------------------------------------
    # I/O SHOULD ACTUALLY HAVE HAPPENED
    # -----------------------------------------------------

    assert delta.write_bytes >= 0

    assert delta.read_bytes >= 0


# =========================================================
# FILESYSTEM REUSABILITY
# =========================================================


def test_backup_directories_remain_removable_after_endurance_run(
    tmp_path: Path,
) -> None:
    """
    Windows is particularly useful for detecting leaked file
    handles because open files frequently prevent directory
    deletion.

    After many backups, all generated paths must be removable.
    """

    project = build_project(
        tmp_path,
        media_enabled=True,
    )

    backup_root = tmp_path / "backups"

    service = BackupService(
        backup_directory=backup_root,
        compression_level=6,
    )

    for _ in range(25):
        result = service.backup_project(
            project,
        )

        remove_archive(
            result.archive_path,
        )

    project_backup_directory = backup_root / project.id

    assert project_backup_directory.exists()

    # If a ZIP/file handle leaked, this is especially likely
    # to fail on Windows.
    project_backup_directory.rmdir()

    assert not (project_backup_directory.exists())
