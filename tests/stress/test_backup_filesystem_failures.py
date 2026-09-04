from __future__ import annotations

import sqlite3
from pathlib import (
    Path,
)
from typing import (
    Any,
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

# =========================================================
# CONFIGURATION
# =========================================================


PROJECT_ID = "filesystem-stress-project"


# =========================================================
# BUILDERS
# =========================================================


def build_sqlite_database(
    database_path: Path,
) -> None:
    """
    Create a real SQLite database for backup stress tests.
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
) -> ProjectSchema:
    database_path = tmp_path / "project.sqlite3"

    build_sqlite_database(
        database_path,
    )

    return ProjectSchema(
        id=PROJECT_ID,
        name="Filesystem Stress Project",
        enabled=True,
        database=DatabaseSchema(
            type=DatabaseType.SQLITE,
            path=database_path,
        ),
        media=MediaSchema(
            enabled=False,
            path=(tmp_path / "media"),
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


def project_backup_directory(
    tmp_path: Path,
) -> Path:
    return tmp_path / "backups" / PROJECT_ID


def list_archives(
    tmp_path: Path,
) -> list[Path]:
    directory = project_backup_directory(
        tmp_path,
    )

    if not directory.exists():
        return []

    return list(directory.glob("*.zip"))


# =========================================================
# PARTIAL ARCHIVE FAILURE
# =========================================================


def test_partial_archive_is_removed_when_archive_creation_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Simulate a disk/write failure after a partial archive
    has already been created.

    BackupService must remove the incomplete ZIP.
    """

    project = build_project(
        tmp_path,
    )

    service = build_service(
        tmp_path,
    )

    def failing_archive_create(
        *,
        archive_path: Path,
        database: object,
        media: object,
    ) -> object:
        del database
        del media

        archive_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        archive_path.write_bytes(b"partial-corrupted-archive")

        assert archive_path.exists()

        raise OSError("Simulated disk write failure.")

    monkeypatch.setattr(
        service._archive_service,
        "create",
        failing_archive_create,
    )

    with pytest.raises(
        OSError,
        match="disk write failure",
    ):
        service.backup_project(
            project,
        )

    assert (
        list_archives(
            tmp_path,
        )
        == []
    )


# =========================================================
# CHECKSUM FAILURE
# =========================================================


def test_completed_archive_is_removed_when_checksum_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Archive creation succeeds but checksum calculation fails.

    The archive must still be considered an incomplete backup
    and removed from the destination directory.
    """

    project = build_project(
        tmp_path,
    )

    service = build_service(
        tmp_path,
    )

    checksum_called = False

    def failing_checksum(
        archive_path: Path,
    ) -> object:
        nonlocal checksum_called

        checksum_called = True

        assert archive_path.exists()

        assert archive_path.stat().st_size > 0

        raise OSError("Simulated checksum read failure.")

    monkeypatch.setattr(
        service._checksum_service,
        "calculate",
        failing_checksum,
    )

    with pytest.raises(
        OSError,
        match="checksum read failure",
    ):
        service.backup_project(
            project,
        )

    assert checksum_called is True

    assert (
        list_archives(
            tmp_path,
        )
        == []
    )


# =========================================================
# CLEANUP FAILURE MUST NOT HIDE ORIGINAL ERROR
# =========================================================


def test_cleanup_failure_does_not_hide_original_backup_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    If deleting a partial archive also fails, BackupService
    must preserve the original backup exception.

    Cleanup errors are deliberately best-effort.
    """

    project = build_project(
        tmp_path,
    )

    service = build_service(
        tmp_path,
    )

    original_unlink = Path.unlink

    partial_archive_path: Path | None = None

    def failing_archive_create(
        *,
        archive_path: Path,
        database: object,
        media: object,
    ) -> object:
        nonlocal partial_archive_path

        del database
        del media

        archive_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        archive_path.write_bytes(b"partial")

        partial_archive_path = archive_path

        raise RuntimeError("Original archive failure.")

    def controlled_unlink(
        path: Path,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        if partial_archive_path is not None and path == partial_archive_path:
            raise PermissionError("Simulated cleanup permission failure.")

        original_unlink(
            path,
            *args,
            **kwargs,
        )

    monkeypatch.setattr(
        service._archive_service,
        "create",
        failing_archive_create,
    )

    monkeypatch.setattr(
        Path,
        "unlink",
        controlled_unlink,
    )

    with pytest.raises(
        RuntimeError,
        match="Original archive failure",
    ):
        service.backup_project(
            project,
        )

    assert partial_archive_path is not None

    # Cleanup itself failed, therefore the partial archive
    # physically remains. The critical invariant here is
    # that the PermissionError did not replace the original
    # RuntimeError.
    assert partial_archive_path.exists()


# =========================================================
# FAILURE RECOVERY
# =========================================================


def test_backup_recovers_after_transient_archive_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    First backup fails after creating a partial archive.

    A later retry must succeed normally without stale partial
    state poisoning the BackupService instance.
    """

    project = build_project(
        tmp_path,
    )

    service = build_service(
        tmp_path,
    )

    original_create = service._archive_service.create

    call_count = 0

    def flaky_archive_create(
        *,
        archive_path: Path,
        database: Any,
        media: Any,
    ) -> Any:
        nonlocal call_count

        call_count += 1

        if call_count == 1:
            archive_path.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            archive_path.write_bytes(b"partial-first-attempt")

            raise OSError("Transient archive failure.")

        return original_create(
            archive_path=archive_path,
            database=database,
            media=media,
        )

    monkeypatch.setattr(
        service._archive_service,
        "create",
        flaky_archive_create,
    )

    # -----------------------------------------------------
    # FIRST ATTEMPT FAILS
    # -----------------------------------------------------

    with pytest.raises(
        OSError,
        match="Transient archive failure",
    ):
        service.backup_project(
            project,
        )

    assert (
        list_archives(
            tmp_path,
        )
        == []
    )

    # -----------------------------------------------------
    # SECOND ATTEMPT SUCCEEDS
    # -----------------------------------------------------

    result = service.backup_project(
        project,
    )

    assert call_count == 2

    assert result.project_id == (project.id)

    assert result.archive_path.exists()

    assert result.archive_path.stat().st_size > 0

    archives = list_archives(
        tmp_path,
    )

    assert len(archives) == 1

    assert archives[0] == (result.archive_path)


# =========================================================
# DESTINATION DIRECTORY FAILURE
# =========================================================


def test_backup_fails_cleanly_when_destination_directory_cannot_be_created(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Simulate permission failure while creating the project's
    backup destination directory.

    No archive should be produced.
    """

    project = build_project(
        tmp_path,
    )

    service = build_service(
        tmp_path,
    )

    expected_project_directory = project_backup_directory(
        tmp_path,
    )

    original_mkdir = Path.mkdir

    def controlled_mkdir(
        path: Path,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        if path == expected_project_directory:
            raise PermissionError(("Simulated destination " "permission failure."))

        original_mkdir(
            path,
            *args,
            **kwargs,
        )

    monkeypatch.setattr(
        Path,
        "mkdir",
        controlled_mkdir,
    )

    with pytest.raises(
        PermissionError,
        match="destination permission failure",
    ):
        service.backup_project(
            project,
        )

    assert not (expected_project_directory.exists())
