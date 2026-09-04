from __future__ import annotations

from datetime import (
    datetime,
    timedelta,
    timezone,
)
from pathlib import Path

from django_assistant_bot.database.models.enums import (
    BackupStatus,
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
from django_assistant_bot.services.backup.retention import (
    RetentionService,
)

# =========================================================
# HELPERS
# =========================================================


def create_project(
    sessions: SessionManager,
) -> str:
    """
    Create a real persisted project for retention tests.
    """

    repository = ProjectRepository(
        sessions,
    )

    project = repository.create(
        ProjectCreateSchema(
            name="retention-integration",
            database=DatabaseSchema(
                path=Path("/srv/retention/db.sqlite3"),
            ),
            media=MediaSchema(
                path=Path("/srv/retention/media"),
            ),
            schedule=ScheduleSchema(
                interval=1,
                unit=ScheduleUnit.HOURS,
            ),
        )
    )

    return project.id


def create_archive(
    directory: Path,
    *,
    name: str,
) -> Path:
    """
    Create a real backup archive file.
    """

    archive_path = directory / name

    archive_path.write_bytes(b"backup-data")

    return archive_path


# =========================================================
# INTEGRATION
# =========================================================


def test_retention_removes_old_archives_and_histories(
    session_manager: SessionManager,
    tmp_path: Path,
) -> None:
    """
    Retention must keep only the newest successful backups
    in both filesystem and database history.
    """

    project_id = create_project(
        session_manager,
    )

    history_repository = BackupHistoryRepository(
        session_manager,
    )

    retention_service = RetentionService(
        history_repository,
    )

    backup_directory = tmp_path / "backups"

    backup_directory.mkdir()

    now = datetime.now(
        timezone.utc,
    )

    oldest_archive = create_archive(
        backup_directory,
        name="backup-oldest.zip",
    )

    middle_archive = create_archive(
        backup_directory,
        name="backup-middle.zip",
    )

    newest_archive = create_archive(
        backup_directory,
        name="backup-newest.zip",
    )

    oldest_history = history_repository.create(
        BackupHistoryCreateSchema(
            project_id=project_id,
            status=BackupStatus.SUCCESS,
            archive_path=oldest_archive,
            archive_size_bytes=100,
            started_at=(
                now
                - timedelta(
                    minutes=20,
                )
            ),
            finished_at=(
                now
                - timedelta(
                    minutes=19,
                )
            ),
        )
    )

    middle_history = history_repository.create(
        BackupHistoryCreateSchema(
            project_id=project_id,
            status=BackupStatus.SUCCESS,
            archive_path=middle_archive,
            archive_size_bytes=100,
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

    newest_history = history_repository.create(
        BackupHistoryCreateSchema(
            project_id=project_id,
            status=BackupStatus.SUCCESS,
            archive_path=newest_archive,
            archive_size_bytes=100,
            started_at=now,
            finished_at=now,
        )
    )

    result = retention_service.cleanup(
        project_id=project_id,
        keep_last=2,
    )

    # -----------------------------------------------------
    # FILESYSTEM
    # -----------------------------------------------------

    assert not oldest_archive.exists()

    assert middle_archive.exists()

    assert newest_archive.exists()

    # -----------------------------------------------------
    # DATABASE
    # -----------------------------------------------------

    assert history_repository.get_by_id(oldest_history.id) is None

    assert history_repository.get_by_id(middle_history.id) is not None

    assert history_repository.get_by_id(newest_history.id) is not None

    successful_histories = history_repository.list_successful_for_project(project_id)

    assert len(successful_histories) == 2

    assert [history.id for history in successful_histories] == [
        newest_history.id,
        middle_history.id,
    ]

    # -----------------------------------------------------
    # RESULT
    # -----------------------------------------------------

    assert result.removed_archives == (oldest_archive,)

    assert result.removed_history_ids == (oldest_history.id,)

    assert result.failed_archives == ()


def test_retention_preserves_failed_history(
    session_manager: SessionManager,
    tmp_path: Path,
) -> None:
    """
    Failed backup history must not participate in
    successful-backup retention.
    """

    project_id = create_project(
        session_manager,
    )

    history_repository = BackupHistoryRepository(
        session_manager,
    )

    retention_service = RetentionService(
        history_repository,
    )

    backup_directory = tmp_path / "backups"

    backup_directory.mkdir()

    now = datetime.now(
        timezone.utc,
    )

    old_success_archive = create_archive(
        backup_directory,
        name="success-old.zip",
    )

    new_success_archive = create_archive(
        backup_directory,
        name="success-new.zip",
    )

    old_success = history_repository.create(
        BackupHistoryCreateSchema(
            project_id=project_id,
            status=BackupStatus.SUCCESS,
            archive_path=old_success_archive,
            started_at=(
                now
                - timedelta(
                    minutes=20,
                )
            ),
            finished_at=(
                now
                - timedelta(
                    minutes=19,
                )
            ),
        )
    )

    failed_history = history_repository.create(
        BackupHistoryCreateSchema(
            project_id=project_id,
            status=BackupStatus.FAILED,
            error_message="database unavailable",
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

    new_success = history_repository.create(
        BackupHistoryCreateSchema(
            project_id=project_id,
            status=BackupStatus.SUCCESS,
            archive_path=new_success_archive,
            started_at=now,
            finished_at=now,
        )
    )

    result = retention_service.cleanup(
        project_id=project_id,
        keep_last=1,
    )

    assert not old_success_archive.exists()

    assert new_success_archive.exists()

    assert history_repository.get_by_id(old_success.id) is None

    assert history_repository.get_by_id(new_success.id) is not None

    preserved_failed = history_repository.get_by_id(failed_history.id)

    assert preserved_failed is not None

    assert preserved_failed.status is BackupStatus.FAILED

    assert preserved_failed.error_message == "database unavailable"

    histories = history_repository.list_for_project(project_id)

    assert len(histories) == 2

    assert {history.id for history in histories} == {
        new_success.id,
        failed_history.id,
    }

    assert result.removed_history_ids == (old_success.id,)


def test_retention_isolated_between_projects(
    session_manager: SessionManager,
    tmp_path: Path,
) -> None:
    """
    Retention for one project must never delete another
    project's backup archive or history.
    """

    project_repository = ProjectRepository(
        session_manager,
    )

    first_project = project_repository.create(
        ProjectCreateSchema(
            name="retention-project-one",
            database=DatabaseSchema(
                path=Path("/srv/project-one/db.sqlite3"),
            ),
            media=MediaSchema(
                path=Path("/srv/project-one/media"),
            ),
            schedule=ScheduleSchema(
                interval=1,
                unit=ScheduleUnit.HOURS,
            ),
        )
    )

    second_project = project_repository.create(
        ProjectCreateSchema(
            name="retention-project-two",
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

    history_repository = BackupHistoryRepository(
        session_manager,
    )

    retention_service = RetentionService(
        history_repository,
    )

    backup_directory = tmp_path / "backups"

    backup_directory.mkdir()

    now = datetime.now(
        timezone.utc,
    )

    first_old_archive = create_archive(
        backup_directory,
        name="first-old.zip",
    )

    first_new_archive = create_archive(
        backup_directory,
        name="first-new.zip",
    )

    second_archive = create_archive(
        backup_directory,
        name="second.zip",
    )

    first_old = history_repository.create(
        BackupHistoryCreateSchema(
            project_id=first_project.id,
            status=BackupStatus.SUCCESS,
            archive_path=first_old_archive,
            started_at=(
                now
                - timedelta(
                    minutes=20,
                )
            ),
            finished_at=(
                now
                - timedelta(
                    minutes=19,
                )
            ),
        )
    )

    first_new = history_repository.create(
        BackupHistoryCreateSchema(
            project_id=first_project.id,
            status=BackupStatus.SUCCESS,
            archive_path=first_new_archive,
            started_at=now,
            finished_at=now,
        )
    )

    second_history = history_repository.create(
        BackupHistoryCreateSchema(
            project_id=second_project.id,
            status=BackupStatus.SUCCESS,
            archive_path=second_archive,
            started_at=(
                now
                - timedelta(
                    minutes=5,
                )
            ),
            finished_at=(
                now
                - timedelta(
                    minutes=4,
                )
            ),
        )
    )

    retention_service.cleanup(
        project_id=first_project.id,
        keep_last=1,
    )

    assert not first_old_archive.exists()

    assert first_new_archive.exists()

    assert second_archive.exists()

    assert history_repository.get_by_id(first_old.id) is None

    assert history_repository.get_by_id(first_new.id) is not None

    assert history_repository.get_by_id(second_history.id) is not None
