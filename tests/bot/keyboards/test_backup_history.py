from __future__ import annotations

from datetime import (
    datetime,
    timezone,
)
from pathlib import Path
from uuid import uuid4

from django_assistant_bot.bot.keyboards.backup_history import (
    build_backup_history_detail_keyboard,
    build_backup_history_list_keyboard,
    build_backup_history_projects_keyboard,
)
from django_assistant_bot.database.models.enums import (
    BackupStatus,
    DatabaseType,
    ScheduleUnit,
)
from django_assistant_bot.schemas.backup import (
    BackupHistorySchema,
)
from django_assistant_bot.schemas.project import (
    DatabaseSchema,
    MediaSchema,
    ProjectSchema,
    ScheduleSchema,
)

TELEGRAM_CALLBACK_DATA_MAX_BYTES = 64


def assert_callback_data_is_valid(
    callback_data: str | None,
) -> None:
    """
    Ensure callback_data satisfies Telegram's 64-byte limit.
    """

    if callback_data is None:
        return

    size_bytes = len(
        callback_data.encode(
            "utf-8",
        )
    )

    assert size_bytes <= TELEGRAM_CALLBACK_DATA_MAX_BYTES, (
        "Telegram callback_data exceeded "
        f"{TELEGRAM_CALLBACK_DATA_MAX_BYTES} bytes: "
        f"{size_bytes} bytes -> {callback_data!r}"
    )


def test_backup_history_callbacks_fit_telegram_limit(
    tmp_path: Path,
) -> None:
    project_id = str(uuid4())

    history_id = str(uuid4())

    project = ProjectSchema(
        id=project_id,
        name="Test Project",
        enabled=True,
        database=DatabaseSchema(
            type=DatabaseType.SQLITE,
            path=(tmp_path / "db.sqlite3"),
        ),
        media=MediaSchema(
            enabled=False,
            path=(tmp_path / "media"),
        ),
        schedule=ScheduleSchema(
            enabled=False,
            interval=1,
            unit=ScheduleUnit.DAYS,
        ),
    )

    now = datetime.now(
        timezone.utc,
    )

    history = BackupHistorySchema(
        id=history_id,
        project_id=project_id,
        status=BackupStatus.SUCCESS,
        archive_path=(tmp_path / "backup.zip"),
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

    keyboards = [
        build_backup_history_projects_keyboard(
            [
                project,
            ]
        ),
        build_backup_history_list_keyboard(
            project_id=project.id,
            histories=[
                history,
            ],
            page=0,
            has_next=True,
        ),
        build_backup_history_detail_keyboard(
            project_id=project.id,
            page=0,
        ),
    ]

    for keyboard in keyboards:
        for row in keyboard.inline_keyboard:
            for button in row:
                assert_callback_data_is_valid(button.callback_data)
