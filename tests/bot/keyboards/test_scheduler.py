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


def test_scheduler_menu_contains_filters(
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

    filter_row = keyboard.inline_keyboard[0]

    assert len(filter_row) == 3

    assert filter_row[0].text == "• همه"

    assert filter_row[0].callback_data == "scheduler"

    assert filter_row[1].text == "فعال"

    assert filter_row[1].callback_data == "sc:f:a"

    assert filter_row[2].text == "غیرفعال"

    assert filter_row[2].callback_data == "sc:f:i"


def test_scheduler_menu_marks_selected_active_filter(
    tmp_path: Path,
) -> None:
    project = build_project(
        tmp_path,
    )

    keyboard = scheduler_menu_keyboard(
        [
            project,
        ],
        selected_filter="a",
    )

    filter_row = keyboard.inline_keyboard[0]

    assert filter_row[0].text == "همه"

    assert filter_row[1].text == "• فعال"

    assert filter_row[2].text == "غیرفعال"


def test_scheduler_menu_marks_selected_inactive_filter(
    tmp_path: Path,
) -> None:
    project = build_project(
        tmp_path,
    )

    keyboard = scheduler_menu_keyboard(
        [
            project,
        ],
        selected_filter="i",
    )

    filter_row = keyboard.inline_keyboard[0]

    assert filter_row[0].text == "همه"

    assert filter_row[1].text == "فعال"

    assert filter_row[2].text == "• غیرفعال"


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

    project_button = keyboard.inline_keyboard[1][0]

    assert project_button.text.startswith("🟢")


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

    project_button = keyboard.inline_keyboard[1][0]

    assert project_button.text.startswith("⚪")


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

    project_button = keyboard.inline_keyboard[1][0]

    assert project_button.text.startswith("🔴")


def test_scheduler_menu_preserves_active_filter_origin(
    tmp_path: Path,
) -> None:
    project = build_project(
        tmp_path,
    )

    keyboard = scheduler_menu_keyboard(
        [
            project,
        ],
        selected_filter="a",
    )

    callbacks = get_callback_data(keyboard)

    assert f"sc:p:{project.id}:a" in callbacks


def test_scheduler_menu_preserves_inactive_filter_origin(
    tmp_path: Path,
) -> None:
    project = build_project(
        tmp_path,
    )

    keyboard = scheduler_menu_keyboard(
        [
            project,
        ],
        selected_filter="i",
    )

    callbacks = get_callback_data(keyboard)

    assert f"sc:p:{project.id}:i" in callbacks


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


def test_project_schedule_back_to_active_filter(
    tmp_path: Path,
) -> None:
    project = build_project(
        tmp_path,
    )

    keyboard = project_schedule_keyboard(
        project,
        "a",
    )

    callbacks = get_callback_data(keyboard)

    assert "sc:f:a" in callbacks


def test_project_schedule_back_to_inactive_filter(
    tmp_path: Path,
) -> None:
    project = build_project(
        tmp_path,
    )

    keyboard = project_schedule_keyboard(
        project,
        "i",
    )

    callbacks = get_callback_data(keyboard)

    assert "sc:f:i" in callbacks


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


def test_interval_menu_back_preserves_active_origin(
    tmp_path: Path,
) -> None:
    project = build_project(
        tmp_path,
    )

    keyboard = schedule_interval_keyboard(
        project.id,
        "a",
    )

    callbacks = get_callback_data(keyboard)

    assert f"sc:p:{project.id}:a" in callbacks


def test_interval_menu_back_preserves_inactive_origin(
    tmp_path: Path,
) -> None:
    project = build_project(
        tmp_path,
    )

    keyboard = schedule_interval_keyboard(
        project.id,
        "i",
    )

    callbacks = get_callback_data(keyboard)

    assert f"sc:p:{project.id}:i" in callbacks


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


def test_unit_menu_preserves_active_origin(
    tmp_path: Path,
) -> None:
    project = build_project(
        tmp_path,
    )

    keyboard = schedule_unit_keyboard(
        project.id,
        "a",
    )

    callbacks = get_callback_data(keyboard)

    assert f"sc:p:{project.id}:a" in callbacks


def test_unit_menu_preserves_inactive_origin(
    tmp_path: Path,
) -> None:
    project = build_project(
        tmp_path,
    )

    keyboard = schedule_unit_keyboard(
        project.id,
        "i",
    )

    callbacks = get_callback_data(keyboard)

    assert f"sc:p:{project.id}:i" in callbacks


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
            ],
            selected_filter="s",
        ),
        scheduler_menu_keyboard(
            [
                project,
            ],
            selected_filter="a",
        ),
        scheduler_menu_keyboard(
            [
                project,
            ],
            selected_filter="i",
        ),
        project_schedule_keyboard(
            project,
            "s",
        ),
        project_schedule_keyboard(
            project,
            "a",
        ),
        project_schedule_keyboard(
            project,
            "i",
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
            "a",
        ),
        schedule_interval_keyboard(
            project.id,
            "i",
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
            "a",
        ),
        schedule_unit_keyboard(
            project.id,
            "i",
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
