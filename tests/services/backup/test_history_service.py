from __future__ import annotations

from datetime import (
    datetime,
    timezone,
)
from pathlib import Path
from unittest.mock import Mock

import pytest

from django_assistant_bot.database.models.enums import (
    BackupStatus,
)
from django_assistant_bot.schemas.backup import (
    BackupHistorySchema,
)
from django_assistant_bot.services.backup.history import (
    BackupHistoryService,
)
from django_assistant_bot.services.backup.history_exceptions import (
    BackupHistoryNotFoundError,
    BackupHistoryValidationError,
)


def build_history(
    *,
    history_id: str = "history-1",
    project_id: str = "project-1",
) -> BackupHistorySchema:
    now = datetime.now(
        timezone.utc,
    )

    return BackupHistorySchema(
        id=history_id,
        project_id=project_id,
        status=BackupStatus.SUCCESS,
        archive_path=Path("C:/backups/test.zip"),
        database_size_bytes=100,
        media_size_bytes=200,
        archive_size_bytes=250,
        media_file_count=5,
        checksum_algorithm="sha256",
        checksum_value="checksum",
        error_message=None,
        started_at=now,
        finished_at=now,
    )


def test_list_for_project() -> None:
    repository = Mock()

    history = build_history()

    repository.list_for_project.return_value = [
        history,
    ]

    service = BackupHistoryService(
        repository,
    )

    result = service.list_for_project(
        "project-1",
        limit=10,
        offset=0,
    )

    assert result == [
        history,
    ]

    repository.list_for_project.assert_called_once_with(
        "project-1",
        limit=10,
        offset=0,
    )


def test_get_history() -> None:
    repository = Mock()

    history = build_history()

    repository.get_by_id.return_value = history

    service = BackupHistoryService(
        repository,
    )

    result = service.get_history(
        history.id,
    )

    assert result == history


def test_get_history_checks_project() -> None:
    repository = Mock()

    history = build_history(
        project_id="project-1",
    )

    repository.get_by_id.return_value = history

    service = BackupHistoryService(
        repository,
    )

    with pytest.raises(
        BackupHistoryNotFoundError,
    ):
        service.get_history(
            history.id,
            project_id="project-2",
        )


def test_unknown_history_fails() -> None:
    repository = Mock()

    repository.get_by_id.return_value = None

    service = BackupHistoryService(
        repository,
    )

    with pytest.raises(
        BackupHistoryNotFoundError,
    ):
        service.get_history(
            "unknown",
        )


@pytest.mark.parametrize(
    "project_id",
    [
        "",
        " ",
        "   ",
    ],
)
def test_empty_project_id_fails(
    project_id: str,
) -> None:
    repository = Mock()

    service = BackupHistoryService(
        repository,
    )

    with pytest.raises(
        BackupHistoryValidationError,
    ):
        service.list_for_project(
            project_id,
        )

    repository.list_for_project.assert_not_called()


def test_invalid_limit_fails() -> None:
    repository = Mock()

    service = BackupHistoryService(
        repository,
    )

    with pytest.raises(
        BackupHistoryValidationError,
    ):
        service.list_for_project(
            "project-1",
            limit=0,
        )


def test_negative_offset_fails() -> None:
    repository = Mock()

    service = BackupHistoryService(
        repository,
    )

    with pytest.raises(
        BackupHistoryValidationError,
    ):
        service.list_for_project(
            "project-1",
            offset=-1,
        )
