from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, Message

from bot.context import ApplicationContext
from bot.keyboards.main import main_menu_keyboard

router = Router(name="common")


def build_welcome_message(
    context: ApplicationContext,
) -> str:
    config = context.config

    project_count = len(config.projects)

    bot_status = "🟢 فعال" if config.bot.enabled else "🔴 غیرفعال"

    backup_status = "🟢 فعال" if config.backup.enabled else "🔴 غیرفعال"

    return (
        "🤖 <b>Django Backup Bot</b>\n"
        "\n"
        f"وضعیت ربات: {bot_status}\n"
        f"وضعیت بکاپ: {backup_status}\n"
        f"تعداد پروژه‌ها: <b>{project_count}</b>\n"
        "\n"
        "یکی از گزینه‌های زیر را انتخاب کنید:"
    )


@router.message(CommandStart())
async def start_handler(
    message: Message,
    context: ApplicationContext,
) -> None:
    await message.answer(
        build_welcome_message(context),
        reply_markup=main_menu_keyboard(),
    )


@router.message(Command("help"))
async def help_handler(
    message: Message,
) -> None:
    await message.answer(
        "ℹ️ <b>راهنما</b>\n"
        "\n"
        "/start — منوی اصلی\n"
        "/project — مدیریت پروژه‌ها\n"
        "/help — نمایش راهنما"
    )


@router.callback_query(F.data == "main:menu")
async def main_menu_callback(
    callback: CallbackQuery,
    context: ApplicationContext,
) -> None:
    await callback.answer()

    if not isinstance(callback.message, Message):
        return

    await callback.message.edit_text(
        build_welcome_message(context),
        reply_markup=main_menu_keyboard(),
    )
