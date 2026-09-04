from __future__ import annotations

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)

from django_assistant_bot.schemas.project import (
    ProjectSchema,
)

# =========================================================
# CALLBACKS
# =========================================================


PROJECTS_MENU_CALLBACK = "projects"
PROJECT_LIST_CALLBACK = "project:list"
MAIN_MENU_CALLBACK = "main:menu"


# =========================================================
# PROJECTS MENU
# =========================================================


def projects_menu_keyboard() -> InlineKeyboardMarkup:
    """
    Build the main project-management keyboard.

    Navigation:
        Main Menu
        └── Projects Menu
    """

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="➕ افزودن پروژه",
                    callback_data="project:create",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="📋 لیست پروژه‌ها",
                    callback_data=PROJECT_LIST_CALLBACK,
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🔙 بازگشت",
                    callback_data=MAIN_MENU_CALLBACK,
                ),
            ],
        ],
    )


# =========================================================
# PROJECT LIST
# =========================================================


def project_list_keyboard(
    projects: list[ProjectSchema],
) -> InlineKeyboardMarkup:
    """
    Build project-list keyboard.

    Navigation:
        Projects Menu
        └── Project List

    The back button must return to the projects menu,
    not directly to the application main menu.
    """

    rows: list[list[InlineKeyboardButton]] = []

    for project in projects:
        status_icon = "🟢" if project.enabled else "🔴"

        rows.append(
            [
                InlineKeyboardButton(
                    text=(f"{status_icon} " f"{project.name}"),
                    callback_data=("project:view:" f"{project.id}"),
                ),
            ]
        )

    rows.append(
        [
            InlineKeyboardButton(
                text="➕ افزودن پروژه",
                callback_data="project:create",
            ),
        ]
    )

    rows.append(
        [
            InlineKeyboardButton(
                text="🔙 بازگشت",
                callback_data=PROJECTS_MENU_CALLBACK,
            ),
        ]
    )

    return InlineKeyboardMarkup(
        inline_keyboard=rows,
    )


# =========================================================
# PROJECT DETAILS
# =========================================================


def project_details_keyboard(
    project_id: str,
    enabled: bool,
) -> InlineKeyboardMarkup:
    """
    Build project-details keyboard.

    Navigation:
        Projects Menu
        └── Project List
            └── Project Details
    """

    toggle_button = (
        InlineKeyboardButton(
            text="🔴 غیرفعال کردن",
            callback_data=("project:disable:" f"{project_id}"),
        )
        if enabled
        else InlineKeyboardButton(
            text="🟢 فعال کردن",
            callback_data=("project:enable:" f"{project_id}"),
        )
    )

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="💾 Backup Now",
                    callback_data=("project:backup:" f"{project_id}"),
                ),
            ],
            [
                toggle_button,
            ],
            [
                InlineKeyboardButton(
                    text="🗑 حذف پروژه",
                    callback_data=("project:delete:" f"{project_id}"),
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🔙 بازگشت",
                    callback_data=PROJECT_LIST_CALLBACK,
                ),
            ],
        ],
    )


# =========================================================
# PROJECT CREATION CONFIRMATION
# =========================================================


def project_confirmation_keyboard() -> InlineKeyboardMarkup:
    """
    Build project-creation confirmation keyboard.
    """

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ تأیید و ایجاد",
                    callback_data="project:create:confirm",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="❌ لغو",
                    callback_data="project:create:cancel",
                ),
            ],
        ],
    )


# =========================================================
# PROJECT SCHEDULE
# =========================================================


def schedule_keyboard() -> InlineKeyboardMarkup:
    """
    Build predefined project backup schedule options.
    """

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="1 دقیقه",
                    callback_data=("project:schedule:" "1:minutes"),
                ),
                InlineKeyboardButton(
                    text="2 دقیقه",
                    callback_data=("project:schedule:" "2:minutes"),
                ),
                InlineKeyboardButton(
                    text="5 دقیقه",
                    callback_data=("project:schedule:" "5:minutes"),
                ),
                InlineKeyboardButton(
                    text="10 دقیقه",
                    callback_data=("project:schedule:" "10:minutes"),
                ),
                InlineKeyboardButton(
                    text="15 دقیقه",
                    callback_data=("project:schedule:" "15:minutes"),
                ),
                InlineKeyboardButton(
                    text="30 دقیقه",
                    callback_data=("project:schedule:" "30:minutes"),
                ),
            ],
            [
                InlineKeyboardButton(
                    text="1 ساعت",
                    callback_data=("project:schedule:" "1:hours"),
                ),
                InlineKeyboardButton(
                    text="3 ساعت",
                    callback_data=("project:schedule:" "3:hours"),
                ),
                InlineKeyboardButton(
                    text="4 ساعت",
                    callback_data=("project:schedule:" "4:hours"),
                ),
            ],
            [
                InlineKeyboardButton(
                    text="6 ساعت",
                    callback_data=("project:schedule:" "6:hours"),
                ),
                InlineKeyboardButton(
                    text="12 ساعت",
                    callback_data=("project:schedule:" "12:hours"),
                ),
            ],
            [
                InlineKeyboardButton(
                    text="24 ساعت",
                    callback_data=("project:schedule:" "24:hours"),
                ),
            ],
        ],
    )


__all__ = [
    "MAIN_MENU_CALLBACK",
    "PROJECT_LIST_CALLBACK",
    "PROJECTS_MENU_CALLBACK",
    "project_confirmation_keyboard",
    "project_details_keyboard",
    "project_list_keyboard",
    "projects_menu_keyboard",
    "schedule_keyboard",
]
