from __future__ import annotations

from datetime import datetime
from html import escape

from django_assistant_bot.database.models.enums import (
    BackupStatus,
)
from django_assistant_bot.schemas.backup import (
    BackupHistorySchema,
)
from django_assistant_bot.utils.formatters import (
    format_size,
)

# =========================================================
# HELPERS
# =========================================================


def format_backup_datetime(
    value: datetime,
) -> str:
    """
    Format backup datetime for Telegram display.
    """

    return value.strftime("%Y-%m-%d %H:%M:%S")


def format_backup_duration(
    *,
    started_at: datetime,
    finished_at: datetime | None,
) -> str | None:
    """
    Format backup duration.
    """

    if finished_at is None:
        return None

    total_seconds = max(
        0,
        int((finished_at - started_at).total_seconds()),
    )

    if total_seconds < 60:
        return f"{total_seconds} ثانیه"

    minutes = total_seconds // 60

    seconds = total_seconds % 60

    return f"{minutes} دقیقه و " f"{seconds} ثانیه"


# =========================================================
# HISTORY MENU
# =========================================================


def format_backup_history_menu() -> str:
    """
    Format backup history navigation page.
    """

    return (
        "🕘 <b>تاریخچه بکاپ‌ها</b>\n"
        "\n"
        "در این بخش می‌توانید بکاپ‌های اخیر "
        "تمام پروژه‌ها یا یک پروژه خاص را مشاهده کنید."
    )


# =========================================================
# GLOBAL HISTORY
# =========================================================


def format_backup_history_all(
    *,
    histories: list[BackupHistorySchema],
    project_names: dict[
        str,
        str,
    ],
    page: int,
) -> str:
    """
    Format global backup history page.
    """

    if not histories:
        return "🕘 <b>تاریخچه همه بکاپ‌ها</b>\n" "\n" "هنوز هیچ بکاپی ثبت نشده است."

    lines: list[str] = [
        "🕘 <b>تاریخچه همه بکاپ‌ها</b>",
        "",
        f"📄 صفحه <b>{page + 1}</b>",
        "",
    ]

    for index, history in enumerate(
        histories,
        start=1,
    ):
        success = history.status is BackupStatus.SUCCESS

        status_icon = "✅" if success else "❌"

        status_text = "موفق" if success else "ناموفق"

        project_name = project_names.get(
            history.project_id,
            history.project_id,
        )

        safe_project_name = escape(
            project_name,
            quote=True,
        )

        lines.extend(
            [
                (f"{status_icon} " f"<b>{safe_project_name}</b>"),
                ("وضعیت: " f"<b>{status_text}</b>"),
                ("🕒 " f"{format_backup_datetime(history.started_at)}"),
            ]
        )

        if success:
            lines.append(("🗜 " f"{format_size(history.archive_size_bytes)}"))

        lines.append("")

    return "\n".join(lines).rstrip()


# =========================================================
# PROJECT HISTORY
# =========================================================


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
            "هنوز هیچ بکاپی برای این پروژه ثبت نشده است."
        )

    lines: list[str] = [
        "🕘 <b>تاریخچه بکاپ‌ها</b>",
        "",
        f"📦 پروژه: <b>{safe_project_name}</b>",
        f"📄 صفحه <b>{page + 1}</b>",
        "",
    ]

    for history in histories:
        success = history.status is BackupStatus.SUCCESS

        status_icon = "✅" if success else "❌"

        status_text = "موفق" if success else "ناموفق"

        lines.extend(
            [
                (f"{status_icon} " f"<b>{status_text}</b>"),
                ("🕒 " f"{format_backup_datetime(history.started_at)}"),
            ]
        )

        if success:
            lines.append(("🗜 " f"{format_size(history.archive_size_bytes)}"))

        lines.append("")

    return "\n".join(lines).rstrip()


# =========================================================
# DETAILS
# =========================================================


def format_backup_history_details(
    history: BackupHistorySchema,
    *,
    project_name: str | None = None,
) -> str:
    """
    Format detailed information for one backup.
    """

    success = history.status is BackupStatus.SUCCESS

    status_text = "✅ موفق" if success else "❌ ناموفق"

    lines: list[str] = [
        "🧾 <b>جزئیات بکاپ</b>",
        "",
        ("وضعیت: " f"<b>{status_text}</b>"),
    ]

    if project_name is not None:
        safe_project_name = escape(
            project_name,
            quote=True,
        )

        lines.append(("📦 پروژه: " f"<b>{safe_project_name}</b>"))

    lines.append(("🕒 شروع: " f"<b>{format_backup_datetime(history.started_at)}</b>"))

    if history.finished_at is not None:
        lines.append(
            ("🏁 پایان: " f"<b>{format_backup_datetime(history.finished_at)}</b>")
        )

    duration = format_backup_duration(
        started_at=history.started_at,
        finished_at=history.finished_at,
    )

    if duration is not None:
        lines.append(("⏱ مدت زمان: " f"<b>{duration}</b>"))

    # -----------------------------------------------------
    # SIZE DETAILS
    # -----------------------------------------------------

    lines.extend(
        [
            "",
            "📊 <b>جزئیات حجم</b>",
            "",
            ("🗄 دیتابیس: " f"<b>{format_size(history.database_size_bytes)}</b>"),
            ("📁 مدیا: " f"<b>{format_size(history.media_size_bytes)}</b>"),
            ("🧾 تعداد فایل‌های مدیا: " f"<b>{history.media_file_count:,}</b>"),
            ("🗜 فایل نهایی: " f"<b>{format_size(history.archive_size_bytes)}</b>"),
        ]
    )

    # -----------------------------------------------------
    # CHECKSUM
    # -----------------------------------------------------

    if history.checksum_value:
        algorithm = escape(
            (history.checksum_algorithm or "checksum"),
            quote=True,
        )

        checksum = escape(
            history.checksum_value,
            quote=True,
        )

        lines.extend(
            [
                "",
                ("🔐 " f"<b>{algorithm.upper()}</b>"),
                f"<code>{checksum}</code>",
            ]
        )

    # -----------------------------------------------------
    # ARCHIVE PATH
    # -----------------------------------------------------

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

    # -----------------------------------------------------
    # ERROR
    # -----------------------------------------------------

    if history.error_message:
        error_message = escape(
            history.error_message,
            quote=True,
        )

        if len(error_message) > 300:
            error_message = f"{error_message[:297]}" "..."

        lines.extend(
            [
                "",
                "⚠️ <b>جزئیات خطا</b>",
                f"<code>{error_message}</code>",
            ]
        )

    return "\n".join(lines)


__all__ = [
    "format_backup_datetime",
    "format_backup_duration",
    "format_backup_history_all",
    "format_backup_history_details",
    "format_backup_history_list",
    "format_backup_history_menu",
]
