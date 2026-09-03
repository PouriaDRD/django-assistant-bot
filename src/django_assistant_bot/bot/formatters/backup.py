from __future__ import annotations

from html import escape

from django_assistant_bot.services.backup.models import (
    BackupResult,
)
from django_assistant_bot.utils.formatters import (
    format_size,
)


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
        "⏳ در حال تهیه نسخه پشتیبان...\n"
        "لطفاً تا پایان عملیات صبر کنید."
    )


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

    return (
        "✅ <b>بکاپ با موفقیت انجام شد</b>\n"
        "\n"
        f"📦 پروژه: <b>{safe_name}</b>\n"
        "\n"
        "🗄 <b>Database</b>\n"
        f"{format_size(result.database_size_bytes)}\n"
        "\n"
        "📁 <b>Media</b>\n"
        f"{format_size(result.media_size_bytes)}\n"
        f"{result.media_file_count:,} فایل\n"
        "\n"
        "🗜 <b>Archive</b>\n"
        f"{format_size(result.archive_size_bytes)}\n"
        "\n"
        "🔐 <b>SHA256</b>\n"
        f"<code>{checksum}</code>\n"
        "\n"
        "⏱ <b>مدت زمان</b>\n"
        f"{result.duration_text}"
    )


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
        "جزئیات خطا در تاریخچه بکاپ ثبت شده است."
    )
