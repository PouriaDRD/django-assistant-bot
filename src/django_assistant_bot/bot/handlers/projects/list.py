from __future__ import annotations

from aiogram import F, Router
from aiogram.types import (
    CallbackQuery,
    Message,
)

from django_assistant_bot.bot.context import ApplicationContext
from django_assistant_bot.bot.formatters.project import (
    format_project_list,
)
from django_assistant_bot.bot.keyboards.projects import (
    project_list_keyboard,
)

router = Router(
    name="projects.list",
)


@router.callback_query(
    F.data == "project:list",
)
async def project_list_callback(
    callback: CallbackQuery,
    context: ApplicationContext,
) -> None:
    projects = context.projects.list_projects()

    await callback.answer()

    if not isinstance(
        callback.message,
        Message,
    ):
        return

    await callback.message.edit_text(
        format_project_list(projects),
        reply_markup=(project_list_keyboard(projects)),
    )


async def send_project_list(
    *,
    message: Message,
    context: ApplicationContext,
) -> None:
    projects = context.projects.list_projects()

    await message.answer(
        format_project_list(projects),
        reply_markup=(project_list_keyboard(projects)),
    )
