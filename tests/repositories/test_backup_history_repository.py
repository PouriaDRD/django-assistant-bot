from __future__ import annotations

from datetime import (
    datetime,
    timedelta,
    timezone,
)
from pathlib import Path

from django_assistant_bot.database.models.enums import (
    BackupStatus,
    DatabaseType,
    ScheduleUnit,
)
from django_assistant_bot.database.session import (
    SessionManager,
)
from django_assistant_bot.repositories.backup_history import (
    BackupHistoryRepository,
)
from django_assistant_bot.repositories.project import (
    ProjectRepository,
)
from django_assistant_bot.schemas.backup import (
    BackupHistoryCreateSchema,
)
from django_assistant_bot.schemas.project import (
    DatabaseSchema,
    MediaSchema,
    ProjectCreateSchema,
    ScheduleSchema,
)

# =========================================================
# HELPERS
# =========================================================


def create_project(
    sessions: SessionManager,
) -> str:
    repository = ProjectRepository(
        sessions,
    )

    project = repository.create(
        ProjectCreateSchema(
            name="backup-test",
            database=DatabaseSchema(
                path=Path("/srv/project/db.sqlite3"),
            ),
            media=MediaSchema(
                path=Path("/srv/project/media"),
            ),
            schedule=ScheduleSchema(
                interval=1,
                unit=ScheduleUnit.HOURS,
            ),
        )
    )

    return project.id


# =========================================================
# CREATE
# =========================================================


def test_create_backup_history(
    session_manager: SessionManager,
) -> None:
    project_id = create_project(
        session_manager,
    )

    repository = BackupHistoryRepository(
        session_manager,
    )

    now = datetime.now(
        timezone.utc,
    )

    history = repository.create(
        BackupHistoryCreateSchema(
            project_id=project_id,
            status=BackupStatus.SUCCESS,
            archive_path=Path("/backups/project.zip"),
            database_size_bytes=100,
            media_size_bytes=200,
            archive_size_bytes=250,
            media_file_count=5,
            checksum_algorithm="sha256",
            checksum_value="abc123",
            started_at=now,
            finished_at=now,
        )
    )

    assert history.id

    assert history.status is BackupStatus.SUCCESS

    assert history.archive_path == Path("/backups/project.zip")

    assert history.database_size_bytes == 100

    assert history.media_size_bytes == 200

    assert history.archive_size_bytes == 250

    assert history.media_file_count == 5


# =========================================================
# LIST
# =========================================================


def test_list_backup_history_for_project(
    session_manager: SessionManager,
) -> None:
    project_id = create_project(
        session_manager,
    )

    repository = BackupHistoryRepository(
        session_manager,
    )

    now = datetime.now(
        timezone.utc,
    )

    repository.create(
        BackupHistoryCreateSchema(
            project_id=project_id,
            status=BackupStatus.SUCCESS,
            started_at=now,
        )
    )

    repository.create(
        BackupHistoryCreateSchema(
            project_id=project_id,
            status=BackupStatus.FAILED,
            error_message="Test error",
            started_at=now,
        )
    )

    histories = repository.list_for_project(
        project_id,
    )

    assert len(histories) == 2


def test_list_all_backup_history_orders_newest_first(
    session_manager: SessionManager,
) -> None:
    first_project_id = create_project(
        session_manager,
    )

    project_repository = ProjectRepository(
        session_manager,
    )

    second_project = project_repository.create(
        ProjectCreateSchema(
            name="second-backup-test",
            database=DatabaseSchema(
                path=Path("/srv/project-two/db.sqlite3"),
            ),
            media=MediaSchema(
                path=Path("/srv/project-two/media"),
            ),
            schedule=ScheduleSchema(
                interval=1,
                unit=ScheduleUnit.HOURS,
            ),
        )
    )

    repository = BackupHistoryRepository(
        session_manager,
    )

    now = datetime.now(
        timezone.utc,
    )

    older = repository.create(
        BackupHistoryCreateSchema(
            project_id=first_project_id,
            status=BackupStatus.SUCCESS,
            started_at=(
                now
                - timedelta(
                    minutes=5,
                )
            ),
        )
    )

    newer = repository.create(
        BackupHistoryCreateSchema(
            project_id=second_project.id,
            status=BackupStatus.FAILED,
            error_message="Test failure",
            started_at=now,
        )
    )

    histories = repository.list_all()

    assert len(histories) == 2

    assert histories[0].id == newer.id

    assert histories[1].id == older.id


# =========================================================
# GET BY ID
# =========================================================


def test_get_backup_history_by_id(
    session_manager: SessionManager,
) -> None:
    project_repository = ProjectRepository(
        session_manager,
    )

    history_repository = BackupHistoryRepository(
        session_manager,
    )

    project = project_repository.create(
        ProjectCreateSchema(
            name="History Project",
            database=DatabaseSchema(
                type=DatabaseType.SQLITE,
                path=Path("C:/absolute/db.sqlite3"),
            ),
            media=MediaSchema(
                enabled=False,
                path=Path("C:/absolute/media"),
            ),
            schedule=ScheduleSchema(
                enabled=False,
                interval=1,
                unit=ScheduleUnit.DAYS,
            ),
        )
    )

    now = datetime.now(
        timezone.utc,
    )

    created = history_repository.create(
        BackupHistoryCreateSchema(
            project_id=project.id,
            status=BackupStatus.SUCCESS,
            started_at=now,
            finished_at=now,
        )
    )

    loaded = history_repository.get_by_id(
        created.id,
    )

    assert loaded is not None

    assert loaded.id == created.id


def test_get_unknown_backup_history_returns_none(
    session_manager: SessionManager,
) -> None:
    repository = BackupHistoryRepository(
        session_manager,
    )

    assert repository.get_by_id("unknown") is None


# =========================================================
# GET LATEST
# =========================================================


def test_get_latest_returns_newest_backup_history(
    session_manager: SessionManager,
) -> None:
    project_id = create_project(
        session_manager,
    )

    repository = BackupHistoryRepository(
        session_manager,
    )

    now = datetime.now(
        timezone.utc,
    )

    older = repository.create(
        BackupHistoryCreateSchema(
            project_id=project_id,
            status=BackupStatus.FAILED,
            error_message="Older failure",
            started_at=(
                now
                - timedelta(
                    minutes=10,
                )
            ),
            finished_at=(
                now
                - timedelta(
                    minutes=9,
                )
            ),
        )
    )

    newest = repository.create(
        BackupHistoryCreateSchema(
            project_id=project_id,
            status=BackupStatus.SUCCESS,
            archive_path=Path("/backups/latest.zip"),
            archive_size_bytes=1024,
            started_at=now,
            finished_at=now,
        )
    )

    result = repository.get_latest()

    assert result is not None

    assert result.id == newest.id

    assert result.id != older.id

    assert result.status is BackupStatus.SUCCESS


def test_get_latest_returns_none_when_history_is_empty(
    session_manager: SessionManager,
) -> None:
    repository = BackupHistoryRepository(
        session_manager,
    )

    result = repository.get_latest()

    assert result is None


def test_list_all_backup_history_supports_pagination(
    session_manager: SessionManager,
) -> None:
    project_id = create_project(
        session_manager,
    )

    repository = BackupHistoryRepository(
        session_manager,
    )

    now = datetime.now(
        timezone.utc,
    )

    for index in range(3):
        repository.create(
            BackupHistoryCreateSchema(
                project_id=project_id,
                status=BackupStatus.SUCCESS,
                started_at=(
                    now
                    + timedelta(
                        minutes=index,
                    )
                ),
            )
        )

    first_page = repository.list_all(
        limit=2,
        offset=0,
    )

    second_page = repository.list_all(
        limit=2,
        offset=2,
    )

    assert len(first_page) == 2

    assert len(second_page) == 1

    assert first_page[0].started_at >= first_page[1].started_at
