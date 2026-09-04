from __future__ import annotations

import logging

from aiogram import (
    F,
    Router,
)
from aiogram.types import (
    CallbackQuery,
    Message,
)

from django_assistant_bot.bot.context import (
    ApplicationContext,
)
from django_assistant_bot.bot.formatters.system_status import (
    format_system_status,
)
from django_assistant_bot.bot.keyboards.system_status import (
    SYSTEM_STATUS_CALLBACK,
    SYSTEM_STATUS_REFRESH_CALLBACK,
    system_status_keyboard,
)
from django_assistant_bot.services.admin import (
    AdminPersistenceError,
)
from django_assistant_bot.services.project import (
    ProjectPersistenceError,
)
from django_assistant_bot.services.settings import (
    SettingsPersistenceError,
)

logger = logging.getLogger(
    __name__,
)


router = Router(
    name="system_status",
)


async def _render_system_status(
    callback: CallbackQuery,
    context: ApplicationContext,
) -> None:
    """
    Load and render current system status.
    """

    try:
        status = context.system_status.get_status()

    except (
        SettingsPersistenceError,
        ProjectPersistenceError,
        AdminPersistenceError,
    ):
        logger.exception("Could not load system status.")

        await callback.answer(
            "خطا در دریافت وضعیت سیستم.",
            show_alert=True,
        )

        return

    await callback.answer()

    if not isinstance(
        callback.message,
        Message,
    ):
        return

    await callback.message.edit_text(
        format_system_status(
            status,
        ),
        reply_markup=(system_status_keyboard()),
    )


@router.callback_query(
    F.data == SYSTEM_STATUS_CALLBACK,
)
async def system_status_callback(
    callback: CallbackQuery,
    context: ApplicationContext,
) -> None:
    """
    Display current application system status.
    """

    await _render_system_status(
        callback,
        context,
    )


@router.callback_query(
    F.data == SYSTEM_STATUS_REFRESH_CALLBACK,
)
async def system_status_refresh_callback(
    callback: CallbackQuery,
    context: ApplicationContext,
) -> None:
    """
    Refresh current application system status.
    """

    await _render_system_status(
        callback,
        context,
    )


__all__ = [
    "router",
    "system_status_callback",
    "system_status_refresh_callback",
]
