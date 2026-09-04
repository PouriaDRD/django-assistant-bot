from __future__ import annotations

from pathlib import Path

from django_assistant_bot.bot.keyboards.projects import (
    MAIN_MENU_CALLBACK,
    PROJECT_LIST_CALLBACK,
    PROJECTS_MENU_CALLBACK,
    project_details_keyboard,
    project_list_keyboard,
    projects_menu_keyboard,
    schedule_keyboard,
)
from django_assistant_bot.core.environment import (
    AppEnvironment,
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

# =========================================================
# HELPERS
# =========================================================


def build_project(
    tmp_path: Path,
    *,
    project_id: str = "project-1",
    name: str = "Test Project",
    enabled: bool = True,
) -> ProjectSchema:
    """
    Build a project schema for keyboard tests.
    """

    return ProjectSchema(
        id=project_id,
        name=name,
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
            enabled=False,
            interval=1,
            unit=ScheduleUnit.DAYS,
        ),
    )


def get_callback_data(
    keyboard,
) -> list[str]:
    """
    Extract non-null callback_data values.
    """

    return [
        button.callback_data
        for row in keyboard.inline_keyboard
        for button in row
        if button.callback_data is not None
    ]


def get_button_texts(
    keyboard,
) -> list[str]:
    """
    Extract all button labels.
    """

    return [button.text for row in keyboard.inline_keyboard for button in row]


# =========================================================
# PROJECTS MENU
# =========================================================


def test_projects_menu_back_returns_to_main_menu() -> None:
    keyboard = projects_menu_keyboard()

    callbacks = get_callback_data(
        keyboard,
    )

    assert MAIN_MENU_CALLBACK in callbacks


# =========================================================
# PROJECT LIST
# =========================================================


def test_project_list_back_returns_to_projects_menu(
    tmp_path: Path,
) -> None:
    project = build_project(
        tmp_path,
    )

    keyboard = project_list_keyboard(
        [
            project,
        ]
    )

    callbacks = get_callback_data(
        keyboard,
    )

    assert PROJECTS_MENU_CALLBACK in callbacks

    assert MAIN_MENU_CALLBACK not in callbacks


def test_empty_project_list_back_returns_to_projects_menu() -> None:
    keyboard = project_list_keyboard(
        [],
    )

    callbacks = get_callback_data(
        keyboard,
    )

    assert PROJECTS_MENU_CALLBACK in callbacks

    assert MAIN_MENU_CALLBACK not in callbacks


# =========================================================
# PROJECT DETAILS
# =========================================================


def test_project_details_back_returns_to_project_list() -> None:
    keyboard = project_details_keyboard(
        project_id="project-1",
        enabled=True,
    )

    callbacks = get_callback_data(
        keyboard,
    )

    assert PROJECT_LIST_CALLBACK in callbacks

    assert PROJECTS_MENU_CALLBACK not in callbacks

    assert MAIN_MENU_CALLBACK not in callbacks


# =========================================================
# NAVIGATION HIERARCHY
# =========================================================


def test_project_navigation_hierarchy(
    tmp_path: Path,
) -> None:
    project = build_project(
        tmp_path,
    )

    projects_menu = projects_menu_keyboard()

    project_list = project_list_keyboard(
        [
            project,
        ]
    )

    project_details = project_details_keyboard(
        project_id=project.id,
        enabled=project.enabled,
    )

    projects_callbacks = get_callback_data(
        projects_menu,
    )

    list_callbacks = get_callback_data(
        project_list,
    )

    details_callbacks = get_callback_data(
        project_details,
    )

    assert MAIN_MENU_CALLBACK in projects_callbacks

    assert PROJECTS_MENU_CALLBACK in list_callbacks

    assert PROJECT_LIST_CALLBACK in details_callbacks


# =========================================================
# DEVELOPMENT SCHEDULE
# =========================================================


def test_development_schedule_has_short_intervals() -> None:
    keyboard = schedule_keyboard(
        environment=(AppEnvironment.DEVELOPMENT),
    )

    callbacks = get_callback_data(
        keyboard,
    )

    assert "project:schedule:1:minutes" in callbacks

    assert "project:schedule:2:minutes" in callbacks

    assert "project:schedule:5:minutes" in callbacks

    assert "project:schedule:10:minutes" in callbacks

    assert "project:schedule:15:minutes" in callbacks


# =========================================================
# TESTING SCHEDULE
# =========================================================


def test_testing_schedule_has_short_intervals() -> None:
    keyboard = schedule_keyboard(
        environment=(AppEnvironment.TESTING),
    )

    callbacks = get_callback_data(
        keyboard,
    )

    assert "project:schedule:1:minutes" in callbacks

    assert "project:schedule:10:minutes" in callbacks


# =========================================================
# PRODUCTION SCHEDULE
# =========================================================


def test_production_schedule_starts_at_15_minutes() -> None:
    keyboard = schedule_keyboard(
        environment=(AppEnvironment.PRODUCTION),
    )

    callbacks = get_callback_data(
        keyboard,
    )

    assert "project:schedule:1:minutes" not in callbacks

    assert "project:schedule:2:minutes" not in callbacks

    assert "project:schedule:5:minutes" not in callbacks

    assert "project:schedule:10:minutes" not in callbacks

    assert "project:schedule:15:minutes" in callbacks

    assert "project:schedule:30:minutes" in callbacks

    assert "project:schedule:1:hours" in callbacks


def test_production_schedule_first_option_is_15_minutes() -> None:
    keyboard = schedule_keyboard(
        environment=(AppEnvironment.PRODUCTION),
    )

    texts = get_button_texts(
        keyboard,
    )

    assert texts[0] == "15 دقیقه"


# =========================================================
# CALLBACK LIMIT
# =========================================================


def test_schedule_callbacks_fit_telegram_limit() -> None:
    for environment in AppEnvironment:
        keyboard = schedule_keyboard(
            environment=environment,
        )

        for callback in get_callback_data(
            keyboard,
        ):
            assert len(callback.encode("utf-8")) <= 64
