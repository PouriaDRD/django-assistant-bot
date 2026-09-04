from __future__ import annotations

from django_assistant_bot.schemas.app_settings import (
    AppSettingsSchema,
)

# =========================================================
# SETTINGS MENU
# =========================================================


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
        "📦 تعداد بکاپ‌های نگهداری‌شده: "
        f"<b>{settings.retention_keep_last}</b>\n"
        "🗜 سطح فشرده‌سازی: "
        f"<b>{settings.compression_level}</b>\n"
        f"🌐 پروکسی: <b>{proxy_status}</b>\n"
        "\n"
        "از گزینه‌های زیر برای مدیریت تنظیمات "
        "استفاده کنید."
    )


# =========================================================
# COMPRESSION LEVEL
# =========================================================


def format_compression_level_menu(
    *,
    current_level: int,
) -> str:
    """
    Format compression-level selection screen.
    """

    return (
        "🗜 <b>سطح فشرده‌سازی</b>\n"
        "\n"
        "سطح فشرده‌سازی فایل‌های بکاپ را انتخاب کنید.\n"
        "\n"
        f"مقدار فعلی: <b>{current_level}</b>\n"
        "\n"
        "• <b>0</b> — بدون فشرده‌سازی\n"
        "• <b>1</b> — سریع‌ترین حالت\n"
        "• <b>6</b> — متعادل و پیشنهادی\n"
        "• <b>9</b> — بیشترین فشرده‌سازی\n"
        "\n"
        "سطح بالاتر معمولاً فایل کوچک‌تری تولید می‌کند، "
        "اما CPU و زمان بیشتری مصرف می‌شود."
    )


# =========================================================
# RETENTION KEEP-LAST
# =========================================================


def format_retention_keep_last_prompt(
    *,
    current_value: int,
) -> str:
    """
    Format retention keep-last input prompt.
    """

    return (
        "📦 <b>تعداد بکاپ‌های نگهداری‌شده</b>\n"
        "\n"
        "تعداد نسخه‌های موفقی که برای هر پروژه "
        "باید نگهداری شوند را وارد کنید.\n"
        "\n"
        f"مقدار فعلی: <b>{current_value}</b>\n"
        "\n"
        "عدد واردشده باید حداقل <b>1</b> باشد.\n"
        "\n"
        "مثال:\n"
        "<code>10</code>"
    )


# =========================================================
# BOT DISABLED
# =========================================================


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
    "format_compression_level_menu",
    "format_retention_keep_last_prompt",
    "format_settings_menu",
]
