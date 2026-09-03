from __future__ import annotations

from aiogram import F, Router
from aiogram.types import (
    CallbackQuery,
    Message,
)

from django_assistant_bot.bot.context import ApplicationContext
from django_assistant_bot.bot.formatters.project import (
    format_project_details,
)
from django_assistant_bot.bot.keyboards.projects import (
    project_details_keyboard,
)
from django_assistant_bot.services.project import (
    ProjectNotFoundError,
)

router = Router(
    name="projects.status",
)


@router.callback_query(
    F.data.startswith("project:enable:"),
)
async def project_enable_callback(
    callback: CallbackQuery,
    context: ApplicationContext,
) -> None:
    await _set_project_status(
        callback=callback,
        context=context,
        enabled=True,
    )


@router.callback_query(
    F.data.startswith("project:disable:"),
)
async def project_disable_callback(
    callback: CallbackQuery,
    context: ApplicationContext,
) -> None:
    await _set_project_status(
        callback=callback,
        context=context,
        enabled=False,
    )


async def _set_project_status(
    *,
    callback: CallbackQuery,
    context: ApplicationContext,
    enabled: bool,
) -> None:
    callback_data = callback.data

    if not callback_data:
        await callback.answer()
        return

    prefix = "project:enable:" if enabled else "project:disable:"

    project_id = callback_data.removeprefix(prefix)

    if not project_id:
        await callback.answer(
            "شناسه پروژه نامعتبر است.",
            show_alert=True,
        )
        return

    try:
        project = context.projects.set_enabled(
            project_id,
            enabled,
        )

    except ProjectNotFoundError:
        await callback.answer(
            "پروژه پیدا نشد.",
            show_alert=True,
        )
        return

    await callback.answer(("پروژه فعال شد." if enabled else "پروژه غیرفعال شد."))

    if not isinstance(
        callback.message,
        Message,
    ):
        return

    await callback.message.edit_text(
        format_project_details(project),
        reply_markup=(
            project_details_keyboard(
                project.id,
                project.enabled,
            )
        ),
    )
