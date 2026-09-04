from __future__ import annotations

from enum import StrEnum

from django_assistant_bot.schemas.admin import (
    AdminSchema,
)


class AdminDeliveryStatus(StrEnum):
    """
    Telegram delivery verification result for a newly
    registered administrator.
    """

    VERIFIED = "verified"

    CHAT_UNAVAILABLE = "chat_unavailable"

    BLOCKED = "blocked"

    TEMPORARY_FAILURE = "temporary_failure"

    API_FAILURE = "api_failure"


def format_admins_menu(
    admins: list[AdminSchema],
) -> str:
    """
    Format administrator management screen.
    """

    count = len(admins)

    lines = [
        "👤 <b>مدیریت ادمین‌ها</b>",
        "",
        f"تعداد ادمین‌ها: <b>{count}</b>",
        "",
    ]

    if not admins:
        lines.append("هیچ ادمینی ثبت نشده است.")

    else:
        lines.append("ادمین‌های فعلی:")

        lines.append("")

        for index, admin in enumerate(
            admins,
            start=1,
        ):
            lines.append(f"{index}. " f"<code>{admin.telegram_user_id}</code>")

    lines.extend(
        [
            "",
            "از گزینه‌های زیر استفاده کنید.",
        ]
    )

    return "\n".join(lines)


def format_add_admin_prompt() -> str:
    """
    Format administrator creation prompt.
    """

    return (
        "➕ <b>افزودن ادمین</b>\n"
        "\n"
        "آیدی عددی Telegram کاربر را ارسال کنید.\n"
        "\n"
        "مثال:\n"
        "<code>123456789</code>\n"
        "\n"
        "پس از افزودن، امکان ارسال پیام به این ادمین "
        "به‌صورت خودکار بررسی می‌شود."
    )


def format_admin_created(
    telegram_user_id: int,
    *,
    delivery_status: AdminDeliveryStatus,
) -> str:
    """
    Format administrator creation result.
    """

    lines = [
        "✅ <b>ادمین اضافه شد</b>",
        "",
        "Telegram ID:",
        f"<code>{telegram_user_id}</code>",
        "",
    ]

    if delivery_status == AdminDeliveryStatus.VERIFIED:
        lines.extend(
            [
                "🟢 <b>ارتباط با تلگرام تأیید شد.</b>",
                "",
                "این ادمین می‌تواند پیام‌ها و فایل‌های " "بکاپ را دریافت کند.",
            ]
        )

    elif delivery_status == AdminDeliveryStatus.BLOCKED:
        lines.extend(
            [
                "🔴 <b>ربات توسط این کاربر Block شده است.</b>",
                "",
                "ادمین با موفقیت ذخیره شده، اما فعلاً "
                "امکان ارسال پیام و فایل بکاپ به او وجود ندارد.",
                "",
                "کاربر باید ابتدا ربات را Unblock کند و سپس "
                "<code>/start</code> را ارسال کند.",
            ]
        )

    elif delivery_status == AdminDeliveryStatus.CHAT_UNAVAILABLE:
        lines.extend(
            [
                "⚠️ <b>گفتگو با این کاربر هنوز در دسترس نیست.</b>",
                "",
                "ادمین با موفقیت ذخیره شده، اما ربات نتوانست "
                "Chat کاربر را پیدا کند.",
                "",
                "کاربر باید ابتدا وارد ربات شود و " "<code>/start</code> را ارسال کند.",
            ]
        )

    elif delivery_status == AdminDeliveryStatus.TEMPORARY_FAILURE:
        lines.extend(
            [
                "🟡 <b>بررسی ارتباط موقتاً ناموفق بود.</b>",
                "",
                "ادمین با موفقیت ذخیره شده است، اما به دلیل "
                "مشکل موقت شبکه امکان بررسی دسترسی وجود نداشت.",
                "",
                "این وضعیت مانع ثبت ادمین نمی‌شود.",
            ]
        )

    else:
        lines.extend(
            [
                "⚠️ <b>امکان تأیید ارتباط با تلگرام وجود نداشت.</b>",
                "",
                "ادمین با موفقیت ذخیره شده است.",
                "",
                "در صورت نیاز، دسترسی این ادمین را بعداً " "دوباره بررسی کنید.",
            ]
        )

    return "\n".join(lines)


def format_admin_welcome() -> str:
    """
    Format verification message sent to a new administrator.
    """

    return (
        "✅ <b>دسترسی ادمین فعال شد</b>\n"
        "\n"
        "شما به‌عنوان ادمین Django Assistant Bot "
        "ثبت شده‌اید.\n"
        "\n"
        "از این پس می‌توانید از امکانات مدیریتی ربات "
        "استفاده کنید و فایل‌های بکاپ را دریافت کنید."
    )


def format_admin_removed(
    telegram_user_id: int,
) -> str:
    """
    Format administrator deletion success message.
    """

    return (
        "✅ <b>ادمین حذف شد</b>\n"
        "\n"
        "Telegram ID:\n"
        f"<code>{telegram_user_id}</code>"
    )


__all__ = [
    "AdminDeliveryStatus",
    "format_add_admin_prompt",
    "format_admin_created",
    "format_admin_removed",
    "format_admin_welcome",
    "format_admins_menu",
]
