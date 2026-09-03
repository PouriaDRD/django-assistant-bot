from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from django_assistant_bot.database.models.enums import (
    BackupStatus,
    ScheduleUnit,
)
from django_assistant_bot.database.session import SessionManager
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
