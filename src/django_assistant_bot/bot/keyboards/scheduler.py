from __future__ import annotations

from typing import Literal

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)

from django_assistant_bot.database.models.enums import (
    ScheduleUnit,
)
from django_assistant_bot.schemas.project import (
    ProjectSchema,
)

ScheduleOrigin = Literal[
    "s",
    "p",
]


# =========================================================
# CALLBACKS
# =========================================================


SCHEDULER_MENU_CALLBACK = "scheduler"

SCHEDULER_PROJECT_PREFIX = "sc:p:"
SCHEDULER_TOGGLE_PREFIX = "sc:t:"

SCHEDULER_INTERVAL_PREFIX = "sc:i:"
SCHEDULER_INTERVAL_SET_PREFIX = "sc:is:"

SCHEDULER_UNIT_PREFIX = "sc:u:"
SCHEDULER_UNIT_SET_PREFIX = "sc:us:"


# =========================================================
# HELPERS
# =========================================================


def build_project_schedule_callback(
    project_id: str,
    origin: ScheduleOrigin,
) -> str:
    """
    Build project schedule callback.
    """

    return f"{SCHEDULER_PROJECT_PREFIX}" f"{project_id}:" f"{origin}"


def build_project_schedule_back_callback(
    project_id: str,
    origin: ScheduleOrigin,
) -> str:
    """
    Build correct back-navigation callback.

    s -> Scheduler menu
    p -> Project details
    """

    if origin == "p":
        return f"project:view:{project_id}"

    return SCHEDULER_MENU_CALLBACK


# =========================================================
# GLOBAL MENU
# =========================================================


def scheduler_menu_keyboard(
    projects: list[ProjectSchema],
) -> InlineKeyboardMarkup:
    """
    Build scheduler project-selection keyboard.
    """

    rows: list[list[InlineKeyboardButton]] = []

    for project in projects:
        if project.enabled and project.schedule.enabled:
            icon = "🟢"

        elif not project.enabled:
            icon = "🔴"

        else:
            icon = "⚪"

        rows.append(
            [
                InlineKeyboardButton(
                    text=(f"{icon} " f"{project.name}"),
                    callback_data=(
                        build_project_schedule_callback(
                            project.id,
                            "s",
                        )
                    ),
                ),
            ]
        )

    rows.append(
        [
            InlineKeyboardButton(
                text="🔙 بازگشت",
                callback_data="main:menu",
            ),
        ]
    )

    return InlineKeyboardMarkup(
        inline_keyboard=rows,
    )


# =========================================================
# PROJECT SCHEDULE
# =========================================================


def project_schedule_keyboard(
    project: ProjectSchema,
    origin: ScheduleOrigin,
) -> InlineKeyboardMarkup:
    """
    Build schedule-management keyboard for one project.
    """

    toggle_text = (
        "⏸ غیرفعال کردن زمان‌بندی"
        if project.schedule.enabled
        else "▶️ فعال کردن زمان‌بندی"
    )

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=toggle_text,
                    callback_data=(
                        f"{SCHEDULER_TOGGLE_PREFIX}" f"{project.id}:" f"{origin}"
                    ),
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🔁 تغییر فاصله اجرا",
                    callback_data=(
                        f"{SCHEDULER_INTERVAL_PREFIX}" f"{project.id}:" f"{origin}"
                    ),
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🕒 تغییر واحد",
                    callback_data=(
                        f"{SCHEDULER_UNIT_PREFIX}" f"{project.id}:" f"{origin}"
                    ),
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🔙 بازگشت",
                    callback_data=(
                        build_project_schedule_back_callback(
                            project.id,
                            origin,
                        )
                    ),
                ),
            ],
        ],
    )


# =========================================================
# INTERVAL
# =========================================================


def schedule_interval_keyboard(
    project_id: str,
    origin: ScheduleOrigin,
) -> InlineKeyboardMarkup:
    """
    Build predefined schedule interval options.

    The selected interval keeps the existing schedule unit.
    """

    intervals = (
        1,
        2,
        5,
        10,
        15,
        30,
    )

    rows: list[list[InlineKeyboardButton]] = []

    for index in range(
        0,
        len(intervals),
        2,
    ):
        row: list[InlineKeyboardButton] = []

        for interval in intervals[index : index + 2]:
            row.append(
                InlineKeyboardButton(
                    text=str(interval),
                    callback_data=(
                        f"{SCHEDULER_INTERVAL_SET_PREFIX}"
                        f"{project_id}:"
                        f"{origin}:"
                        f"{interval}"
                    ),
                )
            )

        rows.append(row)

    rows.append(
        [
            InlineKeyboardButton(
                text="🔙 بازگشت",
                callback_data=(
                    build_project_schedule_callback(
                        project_id,
                        origin,
                    )
                ),
            ),
        ]
    )

    return InlineKeyboardMarkup(
        inline_keyboard=rows,
    )


# =========================================================
# UNIT
# =========================================================


def schedule_unit_keyboard(
    project_id: str,
    origin: ScheduleOrigin,
) -> InlineKeyboardMarkup:
    """
    Build schedule unit selector.
    """

    units = (
        (
            ScheduleUnit.MINUTES,
            "دقیقه",
        ),
        (
            ScheduleUnit.HOURS,
            "ساعت",
        ),
        (
            ScheduleUnit.DAYS,
            "روز",
        ),
    )

    rows: list[list[InlineKeyboardButton]] = []

    for unit, label in units:
        rows.append(
            [
                InlineKeyboardButton(
                    text=label,
                    callback_data=(
                        f"{SCHEDULER_UNIT_SET_PREFIX}"
                        f"{project_id}:"
                        f"{origin}:"
                        f"{unit.value}"
                    ),
                ),
            ]
        )

    rows.append(
        [
            InlineKeyboardButton(
                text="🔙 بازگشت",
                callback_data=(
                    build_project_schedule_callback(
                        project_id,
                        origin,
                    )
                ),
            ),
        ]
    )

    return InlineKeyboardMarkup(
        inline_keyboard=rows,
    )


__all__ = [
    "SCHEDULER_INTERVAL_PREFIX",
    "SCHEDULER_INTERVAL_SET_PREFIX",
    "SCHEDULER_MENU_CALLBACK",
    "SCHEDULER_PROJECT_PREFIX",
    "SCHEDULER_TOGGLE_PREFIX",
    "SCHEDULER_UNIT_PREFIX",
    "SCHEDULER_UNIT_SET_PREFIX",
    "ScheduleOrigin",
    "build_project_schedule_callback",
    "project_schedule_keyboard",
    "schedule_interval_keyboard",
    "schedule_unit_keyboard",
    "scheduler_menu_keyboard",
]
