from __future__ import annotations

from aiogram import (
    F,
    Router,
)
from aiogram.filters import (
    Command,
    CommandStart,
)
from aiogram.types import (
    CallbackQuery,
    Message,
)

from django_assistant_bot.bot.context import (
    ApplicationContext,
)
from django_assistant_bot.bot.keyboards.main import (
    main_menu_keyboard,
)

router = Router(
    name="common",
)


# =========================================================
# START MESSAGE
# =========================================================


def build_start_message() -> str:
    """
    Build the standalone /start welcome message.

    /start intentionally does not render the application
    dashboard or main menu keyboard.

    The administration dashboard is available through
    /menu instead.
    """

    return (
        "👋 <b>به Django Assistant Bot خوش آمدید</b>\n"
        "\n"
        "این ربات برای مدیریت و تهیه نسخه پشتیبان "
        "از پروژه‌های Django طراحی شده است.\n"
        "\n"
        "برای باز کردن منوی مدیریت از دستور زیر "
        "استفاده کنید:\n"
        "\n"
        "👉 /menu"
    )


# =========================================================
# MAIN MENU MESSAGE
# =========================================================


def build_main_menu_message(
    context: ApplicationContext,
) -> str:
    """
    Build the main dashboard message using live
    application services.
    """

    projects = context.projects.list_projects()

    settings = context.settings.get_settings()

    bot_status = "🟢 فعال" if settings.bot_enabled else "🔴 غیرفعال"

    backup_status = "🟢 فعال" if settings.backup_enabled else "🔴 غیرفعال"

    project_count = len(
        projects,
    )

    return (
        "🤖 <b>Django Assistant Bot</b>\n"
        "\n"
        f"وضعیت ربات: {bot_status}\n"
        f"وضعیت بکاپ: {backup_status}\n"
        f"تعداد پروژه‌ها: <b>{project_count}</b>\n"
        "\n"
        "یکی از گزینه‌های زیر را انتخاب کنید:"
    )


# =========================================================
# HELP MESSAGE
# =========================================================


def build_help_message() -> str:
    """
    Build the user-facing command and feature guide.

    The help text remains intentionally concise because
    detailed operations are exposed through the /menu
    dashboard and its inline keyboards.
    """

    return (
        "ℹ️ <b>راهنمای Django Assistant Bot</b>\n"
        "\n"
        "<b>دستورات</b>\n"
        "/start — معرفی ربات\n"
        "/menu — باز کردن پنل مدیریت\n"
        "/help — نمایش این راهنما\n"
        "\n"
        "<b>امکانات پنل مدیریت</b>\n"
        "📦 مدیریت پروژه‌های Django\n"
        "💾 تهیه بکاپ و مشاهده تاریخچه\n"
        "⏰ مدیریت زمان‌بندی خودکار\n"
        "⚙️ تنظیمات بکاپ، نگهداری و فشرده‌سازی\n"
        "👤 مدیریت ادمین‌ها\n"
        "🌐 تنظیم و تست پروکسی Telegram\n"
        "🤖 مشاهده وضعیت سیستم و سرویس‌ها\n"
        "\n"
        "برای استفاده از امکانات بالا، /menu را باز کنید."
    )


# =========================================================
# /START
# =========================================================


@router.message(
    CommandStart(),
)
async def start_handler(
    message: Message,
) -> None:
    """
    Display the standalone bot introduction.

    The main menu is intentionally not attached here.
    """

    await message.answer(
        build_start_message(),
    )


# =========================================================
# /MENU
# =========================================================


@router.message(
    Command("menu"),
)
async def menu_handler(
    message: Message,
    context: ApplicationContext,
) -> None:
    """
    Display the main administration dashboard.
    """

    await message.answer(
        build_main_menu_message(
            context,
        ),
        reply_markup=(main_menu_keyboard()),
    )


# =========================================================
# /HELP
# =========================================================


@router.message(
    Command("help"),
)
async def help_handler(
    message: Message,
) -> None:
    """
    Display the concise application help guide.
    """

    await message.answer(
        build_help_message(),
    )


# =========================================================
# MAIN MENU CALLBACK
# =========================================================


@router.callback_query(
    F.data == "main:menu",
)
async def main_menu_callback(
    callback: CallbackQuery,
    context: ApplicationContext,
) -> None:
    """
    Return to the main administration dashboard.
    """

    await callback.answer()

    if not isinstance(
        callback.message,
        Message,
    ):
        return

    await callback.message.edit_text(
        build_main_menu_message(
            context,
        ),
        reply_markup=(main_menu_keyboard()),
    )


__all__ = [
    "build_help_message",
    "build_main_menu_message",
    "build_start_message",
    "help_handler",
    "main_menu_callback",
    "menu_handler",
    "router",
    "start_handler",
]
