from __future__ import annotations

from pathlib import Path

from django_assistant_bot.bot.keyboards.projects import (
    MAIN_MENU_CALLBACK,
    PROJECT_LIST_CALLBACK,
    PROJECTS_MENU_CALLBACK,
    project_details_keyboard,
    project_list_keyboard,
    projects_menu_keyboard,
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
    Extract non-null callback_data values from a keyboard.
    """

    return [
        button.callback_data
        for row in keyboard.inline_keyboard
        for button in row
        if button.callback_data is not None
    ]


# =========================================================
# PROJECTS MENU
# =========================================================


def test_projects_menu_back_returns_to_main_menu() -> None:
    """
    Projects menu is directly below the application main menu.
    """

    keyboard = projects_menu_keyboard()

    callback_data = get_callback_data(
        keyboard,
    )

    assert MAIN_MENU_CALLBACK in callback_data


# =========================================================
# PROJECT LIST
# =========================================================


def test_project_list_back_returns_to_projects_menu(
    tmp_path: Path,
) -> None:
    """
    Project list must return one level back to projects menu.
    """

    project = build_project(
        tmp_path,
    )

    keyboard = project_list_keyboard(
        [
            project,
        ]
    )

    callback_data = get_callback_data(
        keyboard,
    )

    assert PROJECTS_MENU_CALLBACK in callback_data

    assert MAIN_MENU_CALLBACK not in callback_data


def test_empty_project_list_back_returns_to_projects_menu() -> None:
    """
    Empty project list must preserve the same navigation.
    """

    keyboard = project_list_keyboard(
        [],
    )

    callback_data = get_callback_data(
        keyboard,
    )

    assert PROJECTS_MENU_CALLBACK in callback_data

    assert MAIN_MENU_CALLBACK not in callback_data


# =========================================================
# PROJECT DETAILS
# =========================================================


def test_project_details_back_returns_to_project_list() -> None:
    """
    Project details must return one level back to project list.
    """

    keyboard = project_details_keyboard(
        project_id="project-1",
        enabled=True,
    )

    callback_data = get_callback_data(
        keyboard,
    )

    assert PROJECT_LIST_CALLBACK in callback_data

    assert PROJECTS_MENU_CALLBACK not in callback_data

    assert MAIN_MENU_CALLBACK not in callback_data


# =========================================================
# NAVIGATION HIERARCHY
# =========================================================


def test_project_navigation_hierarchy(
    tmp_path: Path,
) -> None:
    """
    Verify the complete project navigation hierarchy.

    Main
    └── Projects
        └── Project List
            └── Project Details
    """

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

    # Projects -> Main
    assert MAIN_MENU_CALLBACK in projects_callbacks

    # Project List -> Projects
    assert PROJECTS_MENU_CALLBACK in list_callbacks

    # Project Details -> Project List
    assert PROJECT_LIST_CALLBACK in details_callbacks
