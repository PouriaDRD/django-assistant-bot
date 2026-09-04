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
    "s",  # Scheduler - all
    "a",  # Scheduler - active
    "i",  # Scheduler - inactive
    "p",  # Project details
]

ScheduleFilter = Literal[
    "s",  # All
    "a",  # Active
    "i",  # Inactive
]


# =========================================================
# CALLBACKS
# =========================================================


SCHEDULER_MENU_CALLBACK = "scheduler"

SCHEDULER_FILTER_PREFIX = "sc:f:"

SCHEDULER_PROJECT_PREFIX = "sc:p:"
SCHEDULER_TOGGLE_PREFIX = "sc:t:"

SCHEDULER_INTERVAL_PREFIX = "sc:i:"
SCHEDULER_INTERVAL_SET_PREFIX = "sc:is:"

SCHEDULER_UNIT_PREFIX = "sc:u:"
SCHEDULER_UNIT_SET_PREFIX = "sc:us:"


# =========================================================
# CALLBACK BUILDERS
# =========================================================


def build_scheduler_filter_callback(
    schedule_filter: ScheduleFilter,
) -> str:
    """
    Build scheduler filter callback.

    The default "all" filter uses the existing
    main scheduler callback.
    """

    if schedule_filter == "s":
        return SCHEDULER_MENU_CALLBACK

    return f"{SCHEDULER_FILTER_PREFIX}" f"{schedule_filter}"


def build_project_schedule_callback(
    project_id: str,
    origin: ScheduleOrigin,
) -> str:
    """
    Build project schedule-management callback.
    """

    return f"{SCHEDULER_PROJECT_PREFIX}" f"{project_id}:" f"{origin}"


def build_project_schedule_back_callback(
    project_id: str,
    origin: ScheduleOrigin,
) -> str:
    """
    Build correct back-navigation callback.

    Navigation:
        s -> Scheduler / all
        a -> Scheduler / active
        i -> Scheduler / inactive
        p -> Project details
    """

    if origin == "p":
        return f"project:view:" f"{project_id}"

    return build_scheduler_filter_callback(origin)


# =========================================================
# HELPERS
# =========================================================


def _filter_button_text(
    *,
    label: str,
    value: ScheduleFilter,
    selected: ScheduleFilter,
) -> str:
    """
    Mark the currently selected filter.
    """

    if value == selected:
        return f"• {label}"

    return label


def _project_status_icon(
    project: ProjectSchema,
) -> str:
    """
    Return visual status icon for scheduler list.
    """

    if project.enabled and project.schedule.enabled:
        return "🟢"

    if not project.enabled:
        return "🔴"

    return "⚪"


# =========================================================
# GLOBAL SCHEDULER MENU
# =========================================================


def scheduler_menu_keyboard(
    projects: list[ProjectSchema],
    *,
    selected_filter: ScheduleFilter = "s",
) -> InlineKeyboardMarkup:
    """
    Build scheduler project-selection keyboard.

    The supplied projects are expected to already be filtered
    by the handler when active/inactive filtering is used.
    """

    rows: list[list[InlineKeyboardButton]] = [
        [
            InlineKeyboardButton(
                text=_filter_button_text(
                    label="همه",
                    value="s",
                    selected=selected_filter,
                ),
                callback_data=(build_scheduler_filter_callback("s")),
            ),
            InlineKeyboardButton(
                text=_filter_button_text(
                    label="فعال",
                    value="a",
                    selected=selected_filter,
                ),
                callback_data=(build_scheduler_filter_callback("a")),
            ),
            InlineKeyboardButton(
                text=_filter_button_text(
                    label="غیرفعال",
                    value="i",
                    selected=selected_filter,
                ),
                callback_data=(build_scheduler_filter_callback("i")),
            ),
        ],
    ]

    for project in projects:
        rows.append(
            [
                InlineKeyboardButton(
                    text=(f"{_project_status_icon(project)} " f"{project.name}"),
                    callback_data=(
                        build_project_schedule_callback(
                            project.id,
                            selected_filter,
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

    The selected interval keeps the current schedule unit.
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
    "SCHEDULER_FILTER_PREFIX",
    "SCHEDULER_INTERVAL_PREFIX",
    "SCHEDULER_INTERVAL_SET_PREFIX",
    "SCHEDULER_MENU_CALLBACK",
    "SCHEDULER_PROJECT_PREFIX",
    "SCHEDULER_TOGGLE_PREFIX",
    "SCHEDULER_UNIT_PREFIX",
    "SCHEDULER_UNIT_SET_PREFIX",
    "ScheduleFilter",
    "ScheduleOrigin",
    "build_project_schedule_callback",
    "build_scheduler_filter_callback",
    "project_schedule_keyboard",
    "schedule_interval_keyboard",
    "schedule_unit_keyboard",
    "scheduler_menu_keyboard",
]
