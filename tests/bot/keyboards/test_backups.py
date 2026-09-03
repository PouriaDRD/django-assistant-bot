from __future__ import annotations

from pathlib import Path

from django_assistant_bot.bot.keyboards.backups import (
    backup_projects_keyboard,
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


def test_backup_projects_back_button_returns_to_backup_menu(
    tmp_path: Path,
) -> None:
    project = ProjectSchema(
        id="project-1",
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

    keyboard = backup_projects_keyboard(
        [
            project,
        ]
    )

    callback_data = [
        button.callback_data for row in keyboard.inline_keyboard for button in row
    ]

    assert "backup" in callback_data
    assert "main:menu" not in callback_data
