from __future__ import annotations

from html import escape

from django_assistant_bot.services.backup.models import (
    BackupResult,
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
# SUCCESS
# =========================================================


def format_backup_success(
    result: BackupResult,
) -> str:
    """
    Format successful backup result.
    """

    safe_name = escape(
        result.project_name,
        quote=True,
    )

    checksum = escape(
        result.checksum.value,
        quote=True,
    )

    archive_name = escape(
        result.archive_path.name,
        quote=True,
    )

    duration = _format_duration(
        result.duration_seconds,
    )

    return (
        "✅ <b>بکاپ با موفقیت انجام شد</b>\n"
        "\n"
        f"📦 پروژه: <b>{safe_name}</b>\n"
        "\n"
        "📊 <b>جزئیات بکاپ</b>\n"
        "\n"
        "🗄 دیتابیس: "
        f"<b>{format_size(result.database_size_bytes)}</b>\n"
        "📁 مدیا: "
        f"<b>{format_size(result.media_size_bytes)}</b>\n"
        "🧾 تعداد فایل‌های مدیا: "
        f"<b>{result.media_file_count:,}</b>\n"
        "🗜 فایل نهایی: "
        f"<b>{format_size(result.archive_size_bytes)}</b>\n"
        "⏱ مدت زمان: "
        f"<b>{duration}</b>\n"
        "\n"
        "📄 <b>فایل بکاپ</b>\n"
        f"<code>{archive_name}</code>\n"
        "\n"
        "🔐 <b>SHA256</b>\n"
        f"<code>{checksum}</code>"
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
    "format_backup_failed",
    "format_backup_started",
    "format_backup_success",
]
