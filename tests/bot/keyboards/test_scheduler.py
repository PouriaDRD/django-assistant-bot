from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from django_assistant_bot.bot.keyboards.scheduler import (
    build_project_schedule_callback,
    project_schedule_keyboard,
    schedule_interval_keyboard,
    schedule_unit_keyboard,
    scheduler_menu_keyboard,
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

TELEGRAM_CALLBACK_DATA_MAX_BYTES = 64


# =========================================================
# BUILDERS
# =========================================================


def build_project(
    tmp_path: Path,
    *,
    project_id: str | None = None,
    enabled: bool = True,
    schedule_enabled: bool = True,
) -> ProjectSchema:
    return ProjectSchema(
        id=(project_id if project_id is not None else str(uuid4())),
        name="Test Project",
        enabled=enabled,
        database=DatabaseSchema(
            type=DatabaseType.SQLITE,
            path=(tmp_path / "db.sqlite3"),
        ),
        media=MediaSchema(
            enabled=False,
            path=(tmp_path / "media"),
        ),
        schedule=ScheduleSchema(
            enabled=schedule_enabled,
            interval=5,
            unit=ScheduleUnit.MINUTES,
        ),
    )


def get_callback_data(
    keyboard: object,
) -> list[str]:
    """
    Return all non-empty callback_data values.
    """

    inline_keyboard = getattr(
        keyboard,
        "inline_keyboard",
    )

    return [
        button.callback_data
        for row in inline_keyboard
        for button in row
        if button.callback_data is not None
    ]


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
        f"{size_bytes} bytes -> "
        f"{callback_data!r}"
    )


# =========================================================
# GLOBAL MENU
# =========================================================


def test_scheduler_menu_contains_projects(
    tmp_path: Path,
) -> None:
    project = build_project(
        tmp_path,
    )

    keyboard = scheduler_menu_keyboard(
        [
            project,
        ]
    )

    callbacks = get_callback_data(keyboard)

    assert (
        build_project_schedule_callback(
            project.id,
            "s",
        )
        in callbacks
    )

    assert "main:menu" in callbacks


def test_scheduler_menu_marks_active_schedule(
    tmp_path: Path,
) -> None:
    project = build_project(
        tmp_path,
        enabled=True,
        schedule_enabled=True,
    )

    keyboard = scheduler_menu_keyboard(
        [
            project,
        ]
    )

    button = keyboard.inline_keyboard[0][0]

    assert button.text.startswith("🟢")


def test_scheduler_menu_marks_disabled_schedule(
    tmp_path: Path,
) -> None:
    project = build_project(
        tmp_path,
        enabled=True,
        schedule_enabled=False,
    )

    keyboard = scheduler_menu_keyboard(
        [
            project,
        ]
    )

    button = keyboard.inline_keyboard[0][0]

    assert button.text.startswith("⚪")


def test_scheduler_menu_marks_disabled_project(
    tmp_path: Path,
) -> None:
    project = build_project(
        tmp_path,
        enabled=False,
        schedule_enabled=True,
    )

    keyboard = scheduler_menu_keyboard(
        [
            project,
        ]
    )

    button = keyboard.inline_keyboard[0][0]

    assert button.text.startswith("🔴")


# =========================================================
# NAVIGATION
# =========================================================


def test_project_schedule_back_to_scheduler_menu(
    tmp_path: Path,
) -> None:
    project = build_project(
        tmp_path,
    )

    keyboard = project_schedule_keyboard(
        project,
        "s",
    )

    callbacks = get_callback_data(keyboard)

    assert "scheduler" in callbacks

    assert not any(callback.startswith("project:view:") for callback in callbacks)


def test_project_schedule_back_to_project_details(
    tmp_path: Path,
) -> None:
    project = build_project(
        tmp_path,
    )

    keyboard = project_schedule_keyboard(
        project,
        "p",
    )

    callbacks = get_callback_data(keyboard)

    assert f"project:view:{project.id}" in callbacks


def test_interval_menu_back_preserves_scheduler_origin(
    tmp_path: Path,
) -> None:
    project = build_project(
        tmp_path,
    )

    keyboard = schedule_interval_keyboard(
        project.id,
        "s",
    )

    callbacks = get_callback_data(keyboard)

    assert f"sc:p:{project.id}:s" in callbacks


def test_interval_menu_back_preserves_project_origin(
    tmp_path: Path,
) -> None:
    project = build_project(
        tmp_path,
    )

    keyboard = schedule_interval_keyboard(
        project.id,
        "p",
    )

    callbacks = get_callback_data(keyboard)

    assert f"sc:p:{project.id}:p" in callbacks


def test_unit_menu_back_preserves_origin(
    tmp_path: Path,
) -> None:
    project = build_project(
        tmp_path,
    )

    keyboard = schedule_unit_keyboard(
        project.id,
        "p",
    )

    callbacks = get_callback_data(keyboard)

    assert f"sc:p:{project.id}:p" in callbacks


# =========================================================
# CALLBACK LIMIT
# =========================================================


def test_scheduler_callbacks_fit_telegram_limit(
    tmp_path: Path,
) -> None:
    """
    UUID project IDs must still keep every callback
    within Telegram's 64-byte callback_data limit.
    """

    project = build_project(
        tmp_path,
        project_id=str(uuid4()),
    )

    keyboards = [
        scheduler_menu_keyboard(
            [
                project,
            ]
        ),
        project_schedule_keyboard(
            project,
            "s",
        ),
        project_schedule_keyboard(
            project,
            "p",
        ),
        schedule_interval_keyboard(
            project.id,
            "s",
        ),
        schedule_interval_keyboard(
            project.id,
            "p",
        ),
        schedule_unit_keyboard(
            project.id,
            "s",
        ),
        schedule_unit_keyboard(
            project.id,
            "p",
        ),
    ]

    for keyboard in keyboards:
        for row in keyboard.inline_keyboard:
            for button in row:
                assert_callback_data_is_valid(button.callback_data)
