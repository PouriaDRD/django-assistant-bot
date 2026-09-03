from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    Message,
)

from django_assistant_bot.bot.context import ApplicationContext
from django_assistant_bot.bot.handlers.projects.create import (
    start_project_creation,
)
from django_assistant_bot.bot.handlers.projects.list import (
    send_project_list,
)
from django_assistant_bot.bot.keyboards.projects import (
    projects_menu_keyboard,
)

router = Router(
    name="projects.menu",
)


@router.message(
    Command("project"),
)
async def project_command(
    message: Message,
    state: FSMContext,
    context: ApplicationContext,
) -> None:
    command = (message.text or "").strip()

    parts = command.split(maxsplit=1)

    if len(parts) == 1:
        await message.answer(
            "📦 <b>مدیریت پروژه‌ها</b>\n"
            "\n"
            "/project create — افزودن پروژه\n"
            "/project list — لیست پروژه‌ها\n"
            "\n"
            "یا از منوی زیر استفاده کنید:",
            reply_markup=(projects_menu_keyboard()),
        )
        return

    action = parts[1].strip().casefold()

    if action == "create":
        await start_project_creation(
            message=message,
            state=state,
        )
        return

    if action == "list":
        await send_project_list(
            message=message,
            context=context,
        )
        return

    await message.answer(
        "❌ دستور نامعتبر است.\n"
        "\n"
        "استفاده صحیح:\n"
        "<code>/project create</code>\n"
        "<code>/project list</code>"
    )


@router.callback_query(
    F.data == "projects",
)
async def projects_menu_callback(
    callback: CallbackQuery,
) -> None:
    await callback.answer()

    if not isinstance(
        callback.message,
        Message,
    ):
        return

    await callback.message.edit_text(
        "📦 <b>مدیریت پروژه‌ها</b>\n" "\n" "از گزینه‌های زیر استفاده کنید:",
        reply_markup=(projects_menu_keyboard()),
    )
