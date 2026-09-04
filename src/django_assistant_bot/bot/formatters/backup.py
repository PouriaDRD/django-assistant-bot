from __future__ import annotations

from html import escape

from django_assistant_bot.services.backup.models import (
    BackupResult,
    BackupRetentionSummary,
)
from django_assistant_bot.utils.formatters import (
    format_size,
)

# =========================================================
# HELPERS
# =========================================================


def _format_duration(
    seconds: float,
) -> str:
    """
    Format backup duration for Persian Telegram output.
    """

    if seconds < 60:
        return f"{seconds:.1f} ثانیه"

    minutes = int(seconds // 60)

    remaining_seconds = int(seconds % 60)

    return f"{minutes} دقیقه و " f"{remaining_seconds} ثانیه"


def _format_retention_summary(
    retention: BackupRetentionSummary,
) -> str:
    """
    Format retention cleanup summary.
    """

    if retention.cleanup_failed:
        return (
            "🧹 <b>نگهداری بکاپ‌ها</b>\n"
            "\n"
            "⚠️ پاک‌سازی بکاپ‌های قدیمی انجام نشد.\n"
            "بکاپ جدید با موفقیت ایجاد شده است."
        )

    lines: list[str] = [
        "🧹 <b>نگهداری بکاپ‌ها</b>",
        "",
        ("🎯 حد نگهداری: " f"<b>{retention.keep_last}</b>"),
        ("🗑 حذف‌شده: " f"<b>{retention.removed_count}</b>"),
    ]

    if retention.successful_after is not None:
        lines.append(
            ("📦 نسخه‌های باقی‌مانده: " f"<b>{retention.successful_after}</b>")
        )

    if retention.failed_archive_count:
        lines.append(
            ("⚠️ حذف ناموفق فایل‌ها: " f"<b>{retention.failed_archive_count}</b>")
        )

    return "\n".join(lines)


def _format_backup_success(
    result: BackupResult,
    *,
    automatic: bool,
    include_archive_name: bool,
) -> str:
    """
    Build shared successful-backup Telegram output.

    Manual and scheduled backups intentionally share the
    same details and retention summary to keep Telegram UX
    consistent.
    """

    safe_name = escape(
        result.project_name,
        quote=True,
    )

    checksum = escape(
        result.checksum.value,
        quote=True,
    )

    duration = _format_duration(
        result.duration_seconds,
    )

    title = (
        "✅ <b>بکاپ خودکار با موفقیت انجام شد</b>"
        if automatic
        else "✅ <b>بکاپ با موفقیت انجام شد</b>"
    )

    lines: list[str] = [
        title,
        "",
        ("📦 پروژه: " f"<b>{safe_name}</b>"),
        "",
        "📊 <b>جزئیات بکاپ</b>",
        "",
        ("🗄 دیتابیس: " f"<b>{format_size(result.database_size_bytes)}</b>"),
        ("📁 مدیا: " f"<b>{format_size(result.media_size_bytes)}</b>"),
        ("🧾 تعداد فایل‌های مدیا: " f"<b>{result.media_file_count:,}</b>"),
        ("🗜 فایل نهایی: " f"<b>{format_size(result.archive_size_bytes)}</b>"),
        ("⏱ مدت زمان: " f"<b>{duration}</b>"),
    ]

    if include_archive_name:
        archive_name = escape(
            result.archive_path.name,
            quote=True,
        )

        lines.extend(
            [
                "",
                "📄 <b>فایل بکاپ</b>",
                f"<code>{archive_name}</code>",
            ]
        )

    lines.extend(
        [
            "",
            "🔐 <b>SHA256</b>",
            f"<code>{checksum}</code>",
        ]
    )

    if result.retention is not None:
        lines.extend(
            [
                "",
                _format_retention_summary(
                    result.retention,
                ),
            ]
        )

    return "\n".join(lines)


# =========================================================
# START
# =========================================================


def format_backup_started(
    project_name: str,
) -> str:
    """
    Format backup start message.
    """

    safe_name = escape(
        project_name,
        quote=True,
    )

    return (
        "💾 <b>تهیه بکاپ شروع شد</b>\n"
        "\n"
        f"📦 پروژه: <b>{safe_name}</b>\n"
        "\n"
        "⏳ در حال آماده‌سازی نسخه پشتیبان..."
    )


# =========================================================
# MANUAL SUCCESS
# =========================================================


def format_backup_success(
    result: BackupResult,
) -> str:
    """
    Format successful manual backup result.
    """

    return _format_backup_success(
        result,
        automatic=False,
        include_archive_name=True,
    )


# =========================================================
# AUTOMATIC SUCCESS
# =========================================================


def format_automatic_backup_success(
    result: BackupResult,
) -> str:
    """
    Format successful scheduled backup delivery.

    Archive filename is intentionally omitted because the
    backup archive itself is attached to the Telegram
    message.
    """

    return _format_backup_success(
        result,
        automatic=True,
        include_archive_name=False,
    )


# =========================================================
# FAILED
# =========================================================


def format_backup_failed(
    project_name: str,
) -> str:
    """
    Format generic backup failure message.

    Internal exception details are intentionally not exposed
    to Telegram users.
    """

    safe_name = escape(
        project_name,
        quote=True,
    )

    return (
        "❌ <b>تهیه بکاپ ناموفق بود</b>\n"
        "\n"
        f"📦 پروژه: <b>{safe_name}</b>\n"
        "\n"
        "⚠️ عملیات تهیه نسخه پشتیبان با خطا مواجه شد.\n"
        "\n"
        "جزئیات خطا در تاریخچه بکاپ ثبت شده است."
    )


__all__ = [
    "format_automatic_backup_success",
    "format_backup_failed",
    "format_backup_started",
    "format_backup_success",
]
