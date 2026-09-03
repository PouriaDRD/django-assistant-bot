from __future__ import annotations

from aiogram import F, Router
from aiogram.types import (
    CallbackQuery,
    Message,
)

from django_assistant_bot.bot.context import ApplicationContext
from django_assistant_bot.bot.formatters.project import (
    format_project_deleted,
)
from django_assistant_bot.bot.keyboards.projects import (
    projects_menu_keyboard,
)
from django_assistant_bot.services.project import (
    ProjectNotFoundError,
)

router = Router(
    name="projects.delete",
)


@router.callback_query(
    F.data.startswith("project:delete:"),
)
async def project_delete_callback(
    callback: CallbackQuery,
    context: ApplicationContext,
) -> None:
    callback_data = callback.data

    if not callback_data:
        await callback.answer()
        return

    project_id = callback_data.removeprefix("project:delete:")

    if not project_id:
        await callback.answer(
            "شناسه پروژه نامعتبر است.",
            show_alert=True,
        )
        return

    try:
        project = context.projects.delete_project(project_id)

    except ProjectNotFoundError:
        await callback.answer(
            "پروژه پیدا نشد.",
            show_alert=True,
        )
        return

    await callback.answer("پروژه حذف شد.")

    if not isinstance(
        callback.message,
        Message,
    ):
        return

    await callback.message.edit_text(
        format_project_deleted(project),
        reply_markup=(projects_menu_keyboard()),
    )
