from __future__ import annotations

from html import escape
from urllib.parse import (
    urlsplit,
    urlunsplit,
)

from django_assistant_bot.bot.proxy_connection import (
    ProxyConnectionStatus,
    ProxyConnectionTestResult,
)
from django_assistant_bot.schemas.app_settings import (
    AppSettingsSchema,
)

# =========================================================
# MASKING
# =========================================================


def mask_proxy_url(
    proxy_url: str,
) -> str:
    """
    Mask sensitive proxy credentials for display.
    """

    proxy_url = proxy_url.strip()

    if not proxy_url:
        return ""

    parsed = urlsplit(
        proxy_url,
    )

    hostname = parsed.hostname or ""

    if ":" in hostname:
        hostname = f"[{hostname}]"

    try:
        port = parsed.port

    except ValueError:
        port = None

    host = hostname

    if port is not None:
        host = f"{host}:{port}"

    if parsed.username is not None:
        username = parsed.username

        if parsed.password is not None:
            credentials = f"{username}:••••••••"

        else:
            credentials = username

        host = f"{credentials}@{host}"

    return urlunsplit(
        (
            parsed.scheme,
            host,
            "",
            "",
            "",
        )
    )


# =========================================================
# PROXY MENU
# =========================================================


def format_proxy_menu(
    settings: AppSettingsSchema,
) -> str:
    """
    Format the main proxy management page.
    """

    if settings.proxy_enabled:
        status = "🟢 فعال"

    else:
        status = "🔴 غیرفعال"

    if settings.proxy_url:
        proxy_url = escape(
            mask_proxy_url(
                settings.proxy_url,
            )
        )

        proxy_value = f"<code>{proxy_url}</code>"

    else:
        proxy_value = "تنظیم نشده"

    return (
        "🌐 <b>مدیریت پروکسی</b>\n"
        "\n"
        f"وضعیت: {status}\n"
        f"آدرس: {proxy_value}\n"
        "\n"
        "پروتکل‌های پشتیبانی‌شده:\n"
        "• HTTP\n"
        "• SOCKS4\n"
        "• SOCKS5\n"
        "\n"
        "پروکسی برای ارتباط ربات با Telegram "
        "استفاده می‌شود.\n"
        "\n"
        "ℹ️ تغییرات پروکسی پس از راه‌اندازی "
        "مجدد ربات اعمال می‌شوند."
    )


# =========================================================
# URL PROMPT
# =========================================================


def format_proxy_url_prompt(
    settings: AppSettingsSchema,
) -> str:
    """
    Format proxy URL input prompt.
    """

    current_proxy = (
        escape(
            mask_proxy_url(
                settings.proxy_url,
            )
        )
        if settings.proxy_url
        else "تنظیم نشده"
    )

    return (
        "🌐 <b>تنظیم آدرس پروکسی</b>\n"
        "\n"
        f"مقدار فعلی: <code>{current_proxy}</code>\n"
        "\n"
        "آدرس پروکسی جدید را ارسال کنید.\n"
        "\n"
        "نمونه‌ها:\n"
        "<code>http://127.0.0.1:8080</code>\n"
        "<code>socks4://127.0.0.1:1080</code>\n"
        "<code>socks5://127.0.0.1:1080</code>\n"
        "<code>socks5://user:password@host:1080</code>\n"
        "\n"
        "برای امنیت، رمز عبور پس از ذخیره "
        "در رابط کاربری نمایش داده نمی‌شود."
    )


# =========================================================
# CONNECTION TEST
# =========================================================


def format_proxy_test_result(
    result: ProxyConnectionTestResult,
) -> str:
    """
    Format Telegram proxy connectivity test result.
    """

    duration = f"{result.duration_ms} ms"

    if result.status is ProxyConnectionStatus.SUCCESS:
        bot_line = ""

        if result.telegram_username:
            bot_line = "\n" f"ربات: @{escape(result.telegram_username)}"

        return (
            "✅ <b>اتصال پروکسی موفق بود</b>\n"
            "\n"
            "ارتباط با Telegram Bot API "
            "از طریق این پروکسی برقرار شد.\n"
            f"زمان پاسخ: <code>{duration}</code>"
            f"{bot_line}"
        )

    if result.status is ProxyConnectionStatus.TIMEOUT:
        return (
            "⏱ <b>مهلت اتصال به پایان رسید</b>\n"
            "\n"
            "پروکسی در زمان تعیین‌شده پاسخی "
            "از Telegram دریافت نکرد.\n"
            "\n"
            "آدرس، پورت و وضعیت سرور پروکسی "
            "را بررسی کنید."
        )

    if result.status is ProxyConnectionStatus.NETWORK_ERROR:
        return (
            "❌ <b>اتصال پروکسی ناموفق بود</b>\n"
            "\n"
            "برقراری ارتباط شبکه از طریق "
            "پروکسی امکان‌پذیر نبود.\n"
            "\n"
            "آدرس، پورت، نام کاربری، رمز عبور "
            "و دسترسی پروکسی را بررسی کنید."
        )

    if result.status is ProxyConnectionStatus.TELEGRAM_ERROR:
        return (
            "⚠️ <b>Telegram اتصال را نپذیرفت</b>\n"
            "\n"
            "ارتباط شبکه برقرار شد اما درخواست "
            "Telegram Bot API با خطا مواجه شد."
        )

    return (
        "❌ <b>تست پروکسی با خطا مواجه شد</b>\n"
        "\n"
        "امکان تأیید اتصال این پروکسی وجود "
        "نداشت."
    )


__all__ = [
    "format_proxy_menu",
    "format_proxy_test_result",
    "format_proxy_url_prompt",
    "mask_proxy_url",
]
