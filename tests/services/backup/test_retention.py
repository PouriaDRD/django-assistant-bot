from __future__ import annotations

from datetime import (
    datetime,
    timedelta,
    timezone,
)
from pathlib import Path
from unittest.mock import (
    Mock,
)

import pytest

from django_assistant_bot.database.models.enums import (
    BackupStatus,
)
from django_assistant_bot.repositories.exceptions import (
    PersistenceError,
)
from django_assistant_bot.schemas.backup import (
    BackupHistorySchema,
)
from django_assistant_bot.services.backup.exceptions import (
    RetentionError,
)
from django_assistant_bot.services.backup.retention import (
    RetentionService,
)


def build_history(
    *,
    history_id: str,
    project_id: str,
    archive_path: Path,
    started_at: datetime,
) -> BackupHistorySchema:
    return BackupHistorySchema(
        id=history_id,
        project_id=project_id,
        status=BackupStatus.SUCCESS,
        archive_path=archive_path,
        database_size_bytes=100,
        media_size_bytes=200,
        archive_size_bytes=250,
        media_file_count=5,
        checksum_algorithm="sha256",
        checksum_value="checksum",
        error_message=None,
        started_at=started_at,
        finished_at=started_at,
    )


def test_retention_keeps_newest_backups(
    tmp_path: Path,
) -> None:
    repository = Mock()

    now = datetime.now(
        timezone.utc,
    )

    histories: list[BackupHistorySchema] = []

    for index in range(4):
        archive_path = tmp_path / f"backup-{index}.zip"

        archive_path.write_bytes(b"backup")

        histories.append(
            build_history(
                history_id=f"history-{index}",
                project_id="project-1",
                archive_path=archive_path,
                started_at=(
                    now
                    - timedelta(
                        minutes=index,
                    )
                ),
            )
        )

    repository.list_successful_for_project.return_value = histories

    repository.delete_by_id.return_value = True

    service = RetentionService(
        repository,
    )

    result = service.cleanup(
        project_id="project-1",
        keep_last=2,
    )

    first_archive = histories[0].archive_path
    second_archive = histories[1].archive_path
    third_archive = histories[2].archive_path
    fourth_archive = histories[3].archive_path

    assert first_archive is not None
    assert second_archive is not None
    assert third_archive is not None
    assert fourth_archive is not None

    assert first_archive.exists()
    assert second_archive.exists()

    assert not third_archive.exists()
    assert not fourth_archive.exists()

    assert result.removed_history_ids == (
        "history-2",
        "history-3",
    )

    assert repository.delete_by_id.call_count == 2


def test_retention_does_nothing_within_limit(
    tmp_path: Path,
) -> None:
    repository = Mock()

    now = datetime.now(
        timezone.utc,
    )

    archive_path = tmp_path / "backup.zip"

    archive_path.write_bytes(b"backup")

    repository.list_successful_for_project.return_value = [
        build_history(
            history_id="history-1",
            project_id="project-1",
            archive_path=archive_path,
            started_at=now,
        )
    ]

    service = RetentionService(
        repository,
    )

    result = service.cleanup(
        project_id="project-1",
        keep_last=10,
    )

    assert archive_path.exists()

    assert result.removed_archives == ()

    assert result.removed_history_ids == ()

    assert result.failed_archives == ()

    repository.delete_by_id.assert_not_called()


def test_retention_removes_stale_history_when_file_missing(
    tmp_path: Path,
) -> None:
    repository = Mock()

    now = datetime.now(
        timezone.utc,
    )

    newest = tmp_path / "newest.zip"

    newest.write_bytes(b"backup")

    missing = tmp_path / "missing.zip"

    repository.list_successful_for_project.return_value = [
        build_history(
            history_id="history-newest",
            project_id="project-1",
            archive_path=newest,
            started_at=now,
        ),
        build_history(
            history_id="history-old",
            project_id="project-1",
            archive_path=missing,
            started_at=(
                now
                - timedelta(
                    minutes=1,
                )
            ),
        ),
    ]

    repository.delete_by_id.return_value = True

    service = RetentionService(
        repository,
    )

    result = service.cleanup(
        project_id="project-1",
        keep_last=1,
    )

    assert result.removed_history_ids == ("history-old",)

    repository.delete_by_id.assert_called_once_with("history-old")


def test_invalid_keep_last_fails() -> None:
    repository = Mock()

    service = RetentionService(
        repository,
    )

    with pytest.raises(
        RetentionError,
        match="keep_last",
    ):
        service.cleanup(
            project_id="project-1",
            keep_last=0,
        )


def test_empty_project_id_fails() -> None:
    repository = Mock()

    service = RetentionService(
        repository,
    )

    with pytest.raises(
        RetentionError,
        match="Project ID",
    ):
        service.cleanup(
            project_id=" ",
            keep_last=10,
        )


def test_history_persistence_failure_is_wrapped() -> None:
    repository = Mock()

    repository.list_successful_for_project.side_effect = PersistenceError(
        "database unavailable"
    )

    service = RetentionService(
        repository,
    )

    with pytest.raises(
        RetentionError,
        match="retention",
    ):
        service.cleanup(
            project_id="project-1",
            keep_last=10,
        )
