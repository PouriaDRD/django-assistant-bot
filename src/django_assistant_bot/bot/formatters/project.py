from __future__ import annotations

from html import escape

from django_assistant_bot.database.models.enums import ScheduleUnit
from django_assistant_bot.schemas.project import (
    ProjectSchema,
    ScheduleSchema,
)


def escape_html(
    value: object,
) -> str:
    """
    Escape arbitrary values before embedding them
    inside Telegram HTML messages.
    """

    return escape(
        str(value),
        quote=True,
    )


def format_schedule(
    schedule: ScheduleSchema,
) -> str:
    """
    Format a project schedule for Telegram.
    """

    unit_labels: dict[
        ScheduleUnit,
        str,
    ] = {
        ScheduleUnit.MINUTES: "دقیقه",
        ScheduleUnit.HOURS: "ساعت",
        ScheduleUnit.DAYS: "روز",
    }

    unit = unit_labels[schedule.unit]

    return f"{schedule.interval} " f"{unit}"


def format_project_created(
    project: ProjectSchema,
) -> str:
    """
    Format successful project creation.
    """

    name = escape_html(project.name)

    project_id = escape_html(project.id)

    return (
        "✅ <b>پروژه با موفقیت ایجاد شد.</b>\n"
        "\n"
        f"📦 {name}\n"
        f"🆔 <code>{project_id}</code>\n"
        "\n"
        "وضعیت: 🟢 فعال"
    )


def format_project_list(
    projects: list[ProjectSchema],
) -> str:
    """
    Format the registered project list.
    """

    if not projects:
        return "📋 <b>پروژه‌ها</b>\n" "\n" "هیچ پروژه‌ای ثبت نشده است."

    lines: list[str] = [
        "📋 <b>پروژه‌های ثبت‌شده</b>",
        "",
    ]

    for index, project in enumerate(
        projects,
        start=1,
    ):
        status = "🟢 فعال" if project.enabled else "🔴 غیرفعال"

        name = escape_html(project.name)

        lines.append(f"{index}. " f"<b>{name}</b> — " f"{status}")

    lines.extend(
        [
            "",
            ("برای مدیریت یک پروژه، " "روی نام آن بزنید."),
        ]
    )

    return "\n".join(lines)


def format_project_details(
    project: ProjectSchema,
) -> str:
    """
    Format project details.
    """

    status = "🟢 فعال" if project.enabled else "🔴 غیرفعال"

    media_status = "🟢 فعال" if project.media.enabled else "🔴 غیرفعال"

    schedule_status = "🟢 فعال" if project.schedule.enabled else "🔴 غیرفعال"

    name = escape_html(project.name)

    project_id = escape_html(project.id)

    database_path = escape_html(project.database.path)

    media_path = escape_html(project.media.path)

    schedule = escape_html(format_schedule(project.schedule))

    return (
        f"📦 <b>{name}</b>\n"
        "\n"
        f"🆔 <code>{project_id}</code>\n"
        "\n"
        f"وضعیت پروژه: {status}\n"
        "\n"
        "🗄 <b>Database</b>\n"
        f"<code>{database_path}</code>\n"
        "\n"
        "📁 <b>Media</b>\n"
        f"وضعیت: {media_status}\n"
        f"<code>{media_path}</code>\n"
        "\n"
        "⏰ <b>Schedule</b>\n"
        f"وضعیت: {schedule_status}\n"
        f"<code>{schedule}</code>"
    )


def format_project_confirmation(
    *,
    name: str,
    database_path: str,
    media_path: str,
    schedule: ScheduleSchema,
) -> str:
    """
    Format project creation confirmation.
    """

    safe_name = escape_html(name)

    safe_database_path = escape_html(database_path)

    safe_media_path = escape_html(media_path)

    safe_schedule = escape_html(format_schedule(schedule))

    return (
        "🔎 <b>بررسی اطلاعات پروژه</b>\n"
        "\n"
        "📦 نام:\n"
        f"<code>{safe_name}</code>\n"
        "\n"
        "🗄 Database:\n"
        f"<code>{safe_database_path}</code>\n"
        "\n"
        "📁 Media:\n"
        f"<code>{safe_media_path}</code>\n"
        "\n"
        "⏰ Schedule:\n"
        f"<code>{safe_schedule}</code>\n"
        "\n"
        "آیا اطلاعات صحیح است؟"
    )


def format_project_deleted(
    project: ProjectSchema,
) -> str:
    """
    Format successful project deletion.
    """

    name = escape_html(project.name)

    return f"🗑 پروژه <b>{name}</b> " "با موفقیت حذف شد."
