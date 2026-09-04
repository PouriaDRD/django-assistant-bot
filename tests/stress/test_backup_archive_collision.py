from __future__ import annotations

import sqlite3
from datetime import (
    datetime,
    timezone,
    tzinfo,
)
from pathlib import (
    Path,
)
from typing import (
    Self,
)
from unittest.mock import (
    patch,
)

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


PROJECT_ID = "archive-collision-project"


# =========================================================
# FIXED DATETIME
# =========================================================


FIXED_NOW = datetime(
    2026,
    9,
    4,
    12,
    30,
    45,
    tzinfo=timezone.utc,
)


class FixedDateTime(datetime):
    """
    Force all backup runs to use exactly the same timestamp.
    """

    @classmethod
    def now(
        cls,
        tz: tzinfo | None = None,
    ) -> Self:
        if tz is None:
            value = FIXED_NOW.replace(
                tzinfo=None,
            )

        else:
            value = FIXED_NOW.astimezone(
                tz,
            )

        return cls(
            value.year,
            value.month,
            value.day,
            value.hour,
            value.minute,
            value.second,
            value.microsecond,
            tzinfo=value.tzinfo,
            fold=value.fold,
        )


# =========================================================
# BUILDERS
# =========================================================


def build_database(
    database_path: Path,
) -> None:
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

        connection.execute(
            """
            INSERT INTO stress_data (value)
            VALUES (?);
            """,
            ("initial-value",),
        )

        connection.commit()

    finally:
        connection.close()


def build_project(
    tmp_path: Path,
) -> ProjectSchema:
    database_path = tmp_path / "project.sqlite3"

    build_database(
        database_path,
    )

    return ProjectSchema(
        id=PROJECT_ID,
        name="Archive Collision Project",
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


# =========================================================
# TWO BACKUPS
# =========================================================


def test_two_successful_backups_in_same_second_use_unique_archive_paths(
    tmp_path: Path,
) -> None:
    """
    Two valid backups created at exactly the same timestamp
    must never overwrite each other.

    Both archives must remain independently accessible.
    """

    project = build_project(
        tmp_path,
    )

    service = build_service(
        tmp_path,
    )

    with patch(
        ("django_assistant_bot.services." "backup.service.datetime"),
        FixedDateTime,
    ):
        first = service.backup_project(
            project,
        )

        # -------------------------------------------------
        # MODIFY DATABASE BETWEEN BACKUPS
        # -------------------------------------------------

        connection = sqlite3.connect(
            project.database.path,
        )

        try:
            connection.execute(
                """
                INSERT INTO stress_data (value)
                VALUES (?);
                """,
                ("second-backup-value",),
            )

            connection.commit()

        finally:
            connection.close()

        second = service.backup_project(
            project,
        )

    # -----------------------------------------------------
    # BOTH BACKUPS MUST EXIST
    # -----------------------------------------------------

    assert first.archive_path.exists()

    assert second.archive_path.exists()

    # -----------------------------------------------------
    # CRITICAL INVARIANT
    # -----------------------------------------------------

    assert first.archive_path != second.archive_path, (
        "Two backups created at the same timestamp "
        "resolved to the same archive path."
    )

    # -----------------------------------------------------
    # CHECKSUMS SHOULD ALSO DIFFER
    # -----------------------------------------------------
    #
    # The database was modified between backups, so this
    # additionally verifies that the first archive was not
    # silently overwritten by the second backup.
    # -----------------------------------------------------

    assert first.checksum.value != second.checksum.value

    # -----------------------------------------------------
    # BOTH ARCHIVES MUST BE PRESENT
    # -----------------------------------------------------

    project_directory = tmp_path / "backups" / PROJECT_ID

    archives = list(project_directory.glob("*.zip"))

    assert len(archives) == 2


# =========================================================
# COLLISION STORM
# =========================================================


def test_repeated_same_second_backups_never_reuse_archive_name(
    tmp_path: Path,
) -> None:
    """
    Stress archive-name uniqueness repeatedly while every
    backup receives exactly the same datetime.
    """

    project = build_project(
        tmp_path,
    )

    service = build_service(
        tmp_path,
    )

    results = []

    with patch(
        ("django_assistant_bot.services." "backup.service.datetime"),
        FixedDateTime,
    ):
        for _ in range(20):
            results.append(
                service.backup_project(
                    project,
                )
            )

    archive_paths = {result.archive_path for result in results}

    assert len(archive_paths) == 20

    project_directory = tmp_path / "backups" / PROJECT_ID

    disk_archives = set(project_directory.glob("*.zip"))

    assert disk_archives == archive_paths

    for archive_path in archive_paths:
        assert archive_path.exists()

        assert archive_path.stat().st_size > 0
