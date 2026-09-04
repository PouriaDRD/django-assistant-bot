from __future__ import annotations

from django_assistant_bot.schemas.app_settings import (
    AppSettingsSchema,
)


def format_settings_menu(
    settings: AppSettingsSchema,
) -> str:
    """
    Format runtime application settings for Telegram.
    """

    bot_status = "🟢 فعال" if settings.bot_enabled else "🔴 غیرفعال"

    backup_status = "🟢 فعال" if settings.backup_enabled else "🔴 غیرفعال"

    retention_status = "🟢 فعال" if settings.retention_enabled else "🔴 غیرفعال"

    proxy_status = "🟢 فعال" if settings.proxy_enabled else "⚪ غیرفعال"

    return (
        "⚙️ <b>تنظیمات</b>\n"
        "\n"
        f"🤖 وضعیت ربات: <b>{bot_status}</b>\n"
        f"💾 سیستم بکاپ: <b>{backup_status}</b>\n"
        f"🧹 نگهداری بکاپ‌ها: <b>{retention_status}</b>\n"
        f"🌐 پروکسی: <b>{proxy_status}</b>\n"
        "\n"
        "از گزینه‌های زیر برای مدیریت تنظیمات "
        "استفاده کنید."
    )


def format_bot_disabled() -> str:
    """
    Format the global disabled-state screen.
    """

    return (
        "🔴 <b>ربات غیرفعال شد</b>\n"
        "\n"
        "تمام فعالیت‌های ربات متوقف شده‌اند.\n"
        "\n"
        "• بکاپ دستی غیرفعال است\n"
        "• بکاپ زمان‌بندی‌شده اجرا نمی‌شود\n"
        "• مدیریت پروژه‌ها در دسترس نیست\n"
        "• سایر بخش‌های مدیریتی غیرفعال هستند\n"
        "\n"
        "Polling تلگرام فعال باقی می‌ماند تا بتوانید "
        "ربات را دوباره فعال کنید."
    )


__all__ = [
    "format_bot_disabled",
    "format_settings_menu",
]
