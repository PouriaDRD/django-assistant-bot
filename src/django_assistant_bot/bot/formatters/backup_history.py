from __future__ import annotations

from html import escape
from datetime import datetime

from django_assistant_bot.database.models.enums import (
    BackupStatus,
)
from django_assistant_bot.schemas.backup import (
    BackupHistorySchema,
)
from django_assistant_bot.utils.formatters import (
    format_size,
)


def format_backup_history_menu() -> str:
    """
    Format backup history project-selection page.
    """

    return (
        "🕘 <b>تاریخچه بکاپ‌ها</b>\n"
        "\n"
        "برای مشاهده تاریخچه بکاپ، "
        "پروژه مورد نظر را انتخاب کنید."
    )


def format_backup_history_list(
    *,
    project_name: str,
    histories: list[BackupHistorySchema],
    page: int,
) -> str:
    """
    Format a page of project backup history.
    """

    safe_project_name = escape(
        project_name,
        quote=True,
    )

    if not histories:
        return (
            "🕘 <b>تاریخچه بکاپ‌ها</b>\n"
            "\n"
            f"📦 پروژه: <b>{safe_project_name}</b>\n"
            "\n"
            "هنوز هیچ بکاپی برای این پروژه "
            "ثبت نشده است."
        )

    lines: list[str] = [
        "🕘 <b>تاریخچه بکاپ‌ها</b>",
        "",
        f"📦 پروژه: <b>{safe_project_name}</b>",
        f"📄 صفحه: <b>{page + 1}</b>",
        "",
    ]

    for index, history in enumerate(
        histories,
        start=1,
    ):
        status_icon = "✅" if history.status is BackupStatus.SUCCESS else "❌"

        lines.extend(
            [
                (f"{status_icon} " f"<b>بکاپ #{index}</b>"),
                ("🕒 " f"{format_backup_datetime(history.started_at)}"),
                ("🗜 " f"{format_size(history.archive_size_bytes)}"),
                "",
            ]
        )

    return "\n".join(lines).rstrip()


def format_backup_history_details(
    history: BackupHistorySchema,
) -> str:
    """
    Format detailed information for one backup.
    """

    success = history.status is BackupStatus.SUCCESS

    status_text = "✅ موفق" if success else "❌ ناموفق"

    lines: list[str] = [
        "🧾 <b>جزئیات بکاپ</b>",
        "",
        f"وضعیت: <b>{status_text}</b>",
        ("🕒 شروع: " f"<b>{format_backup_datetime(history.started_at)}</b>"),
    ]

    if history.finished_at is not None:
        lines.append(
            ("🏁 پایان: " f"<b>{format_backup_datetime(history.finished_at)}</b>")
        )

    lines.extend(
        [
            "",
            "🗄 <b>Database</b>",
            format_size(history.database_size_bytes),
            "",
            "📁 <b>Media</b>",
            format_size(history.media_size_bytes),
            (f"{history.media_file_count:,} " "فایل"),
            "",
            "🗜 <b>Archive</b>",
            format_size(history.archive_size_bytes),
        ]
    )

    if history.checksum_value:
        algorithm = escape(
            history.checksum_algorithm or "checksum",
            quote=True,
        )

        checksum = escape(
            history.checksum_value,
            quote=True,
        )

        lines.extend(
            [
                "",
                f"🔐 <b>{algorithm.upper()}</b>",
                f"<code>{checksum}</code>",
            ]
        )

    if history.archive_path is not None:
        archive_path = escape(
            str(history.archive_path),
            quote=True,
        )

        lines.extend(
            [
                "",
                "📍 <b>مسیر فایل</b>",
                f"<code>{archive_path}</code>",
            ]
        )

    if history.error_message:
        error_message = escape(
            history.error_message,
            quote=True,
        )

        lines.extend(
            [
                "",
                "⚠️ <b>خطا</b>",
                f"<code>{error_message}</code>",
            ]
        )

    return "\n".join(lines)


def format_backup_datetime(
    value: datetime,
) -> str:
    """
    Format backup datetime for Telegram display.
    """

    return value.strftime("%Y-%m-%d %H:%M:%S")
