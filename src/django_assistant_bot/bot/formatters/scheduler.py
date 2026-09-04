from __future__ import annotations

from html import escape
from typing import Literal

from django_assistant_bot.database.models.enums import (
    ScheduleUnit,
)
from django_assistant_bot.schemas.project import (
    ProjectSchema,
)

ScheduleFilter = Literal[
    "s",
    "a",
    "i",
]


# =========================================================
# UNIT
# =========================================================


def format_schedule_unit(
    unit: ScheduleUnit,
) -> str:
    """
    Return Persian label for schedule unit.
    """

    labels = {
        ScheduleUnit.MINUTES: "دقیقه",
        ScheduleUnit.HOURS: "ساعت",
        ScheduleUnit.DAYS: "روز",
    }

    return labels[unit]


# =========================================================
# STATUS
# =========================================================


def format_schedule_status(
    project: ProjectSchema,
) -> str:
    """
    Return effective project scheduler status.
    """

    if not project.enabled:
        return "🔴 پروژه غیرفعال"

    if not project.schedule.enabled:
        return "⚪ زمان‌بندی غیرفعال"

    return "🟢 فعال"


# =========================================================
# FILTER
# =========================================================


def format_schedule_filter(
    schedule_filter: ScheduleFilter,
) -> str:
    """
    Return Persian label for scheduler filter.
    """

    labels: dict[
        ScheduleFilter,
        str,
    ] = {
        "s": "همه",
        "a": "فعال",
        "i": "غیرفعال",
    }

    return labels[schedule_filter]


# =========================================================
# SCHEDULER MENU
# =========================================================


def format_scheduler_menu(
    projects: list[ProjectSchema],
    *,
    selected_filter: ScheduleFilter = "s",
) -> str:
    """
    Format global scheduler-management menu.

    Counts are always calculated from all projects.
    Filtering only affects the keyboard project list.
    """

    total = len(projects)

    active = sum(
        1 for project in projects if (project.enabled and project.schedule.enabled)
    )

    inactive = total - active

    filter_label = format_schedule_filter(selected_filter)

    return (
        "⏰ <b>مدیریت زمان‌بندی بکاپ‌ها</b>\n"
        "\n"
        "از این بخش می‌توانید زمان‌بندی بکاپ "
        "پروژه‌ها را مدیریت کنید.\n"
        "\n"
        f"📦 تعداد پروژه‌ها: <b>{total}</b>\n"
        f"🟢 فعال: <b>{active}</b>\n"
        f"⚪ غیرفعال: <b>{inactive}</b>\n"
        "\n"
        f"🔎 نمایش: <b>{filter_label}</b>"
    )


# =========================================================
# PROJECT SCHEDULE
# =========================================================


def format_project_schedule(
    project: ProjectSchema,
) -> str:
    """
    Format schedule details for one project.
    """

    project_name = escape(
        project.name,
        quote=True,
    )

    status = format_schedule_status(project)

    unit = format_schedule_unit(project.schedule.unit)

    effective_note = ""

    if not project.enabled:
        effective_note = (
            "\n\n"
            "⚠️ پروژه غیرفعال است؛ بنابراین زمان‌بندی "
            "تا زمان فعال شدن پروژه اجرا نخواهد شد."
        )

    return (
        "⏰ <b>زمان‌بندی بکاپ</b>\n"
        "\n"
        f"📦 پروژه: <b>{project_name}</b>\n"
        f"📌 وضعیت: <b>{status}</b>\n"
        "\n"
        f"🔁 فاصله اجرا: "
        f"<b>{project.schedule.interval} {unit}</b>"
        f"{effective_note}"
    )


# =========================================================
# INTERVAL MENU
# =========================================================


def format_schedule_interval_menu(
    project: ProjectSchema,
) -> str:
    """
    Format interval-selection menu.
    """

    project_name = escape(
        project.name,
        quote=True,
    )

    unit = format_schedule_unit(project.schedule.unit)

    return (
        "🔁 <b>تغییر فاصله اجرا</b>\n"
        "\n"
        f"📦 پروژه: <b>{project_name}</b>\n"
        f"⏱ فاصله فعلی: "
        f"<b>{project.schedule.interval} {unit}</b>\n"
        "\n"
        "فاصله جدید را انتخاب کنید:"
    )


# =========================================================
# UNIT MENU
# =========================================================


def format_schedule_unit_menu(
    project: ProjectSchema,
) -> str:
    """
    Format schedule unit-selection menu.
    """

    project_name = escape(
        project.name,
        quote=True,
    )

    current_unit = format_schedule_unit(project.schedule.unit)

    return (
        "🕒 <b>تغییر واحد زمان‌بندی</b>\n"
        "\n"
        f"📦 پروژه: <b>{project_name}</b>\n"
        f"📌 واحد فعلی: <b>{current_unit}</b>\n"
        "\n"
        "واحد جدید را انتخاب کنید:"
    )


__all__ = [
    "format_project_schedule",
    "format_schedule_filter",
    "format_schedule_interval_menu",
    "format_schedule_status",
    "format_schedule_unit",
    "format_schedule_unit_menu",
    "format_scheduler_menu",
]
