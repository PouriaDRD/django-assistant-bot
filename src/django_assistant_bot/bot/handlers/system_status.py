from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable

from aiogram import (
    F,
    Router,
)
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardMarkup,
    Message,
)

from django_assistant_bot.bot.context import (
    ApplicationContext,
)
from django_assistant_bot.bot.formatters.system_status import (
    format_system_backup,
    format_system_information,
    format_system_projects,
    format_system_resources,
    format_system_services,
    format_system_status,
)
from django_assistant_bot.bot.keyboards.system_status import (
    SYSTEM_STATUS_BACKUP_CALLBACK,
    SYSTEM_STATUS_CALLBACK,
    SYSTEM_STATUS_OVERVIEW_CALLBACK,
    SYSTEM_STATUS_PROJECTS_CALLBACK,
    SYSTEM_STATUS_REFRESH_CALLBACK,
    SYSTEM_STATUS_RESOURCES_CALLBACK,
    SYSTEM_STATUS_SERVICES_CALLBACK,
    SYSTEM_STATUS_SYSTEM_CALLBACK,
    system_status_detail_keyboard,
    system_status_keyboard,
)
from django_assistant_bot.schemas.system_status import (
    SystemStatusSchema,
)
from django_assistant_bot.services.admin import (
    AdminPersistenceError,
)
from django_assistant_bot.services.backup.history_exceptions import (
    BackupHistoryPersistenceError,
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


Formatter = Callable[
    [SystemStatusSchema],
    str,
]


# =========================================================
# STATUS LOADING
# =========================================================


async def _load_status(
    callback: CallbackQuery,
    context: ApplicationContext,
) -> SystemStatusSchema | None:
    """
    Load current system status without blocking
    the Telegram event loop.
    """

    try:
        return await asyncio.to_thread(context.system_status.get_status)

    except (
        SettingsPersistenceError,
        ProjectPersistenceError,
        AdminPersistenceError,
        BackupHistoryPersistenceError,
    ):
        logger.exception("Could not load system status.")

        await callback.answer(
            "خطا در دریافت وضعیت سیستم.",
            show_alert=True,
        )

        return None


# =========================================================
# PAGE RENDERING
# =========================================================


async def _render_page(
    callback: CallbackQuery,
    context: ApplicationContext,
    *,
    formatter: Formatter,
    keyboard: InlineKeyboardMarkup,
) -> None:
    """
    Load system status and render requested dashboard page.
    """

    status = await _load_status(
        callback,
        context,
    )

    if status is None:
        return

    await callback.answer()

    if not isinstance(
        callback.message,
        Message,
    ):
        return

    await callback.message.edit_text(
        formatter(status),
        reply_markup=keyboard,
    )


async def _render_overview(
    callback: CallbackQuery,
    context: ApplicationContext,
) -> None:
    """
    Render main system-status dashboard.
    """

    await _render_page(
        callback,
        context,
        formatter=(format_system_status),
        keyboard=(system_status_keyboard()),
    )


# =========================================================
# OVERVIEW
# =========================================================


@router.callback_query(
    F.data == SYSTEM_STATUS_CALLBACK,
)
async def system_status_callback(
    callback: CallbackQuery,
    context: ApplicationContext,
) -> None:
    """
    Open system-status dashboard.
    """

    await _render_overview(
        callback,
        context,
    )


@router.callback_query(
    F.data == SYSTEM_STATUS_OVERVIEW_CALLBACK,
)
async def system_status_overview_callback(
    callback: CallbackQuery,
    context: ApplicationContext,
) -> None:
    """
    Return to system-status dashboard.
    """

    await _render_overview(
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
    Refresh main system-status dashboard.
    """

    await _render_overview(
        callback,
        context,
    )


# =========================================================
# SERVICES
# =========================================================


@router.callback_query(
    F.data == SYSTEM_STATUS_SERVICES_CALLBACK,
)
async def system_status_services_callback(
    callback: CallbackQuery,
    context: ApplicationContext,
) -> None:
    """
    Display application service status.
    """

    await _render_page(
        callback,
        context,
        formatter=(format_system_services),
        keyboard=(
            system_status_detail_keyboard(
                refresh_callback=(SYSTEM_STATUS_SERVICES_CALLBACK),
            )
        ),
    )


# =========================================================
# RESOURCES
# =========================================================


@router.callback_query(
    F.data == SYSTEM_STATUS_RESOURCES_CALLBACK,
)
async def system_status_resources_callback(
    callback: CallbackQuery,
    context: ApplicationContext,
) -> None:
    """
    Display host resource usage.
    """

    await _render_page(
        callback,
        context,
        formatter=(format_system_resources),
        keyboard=(
            system_status_detail_keyboard(
                refresh_callback=(SYSTEM_STATUS_RESOURCES_CALLBACK),
            )
        ),
    )


# =========================================================
# BACKUP
# =========================================================


@router.callback_query(
    F.data == SYSTEM_STATUS_BACKUP_CALLBACK,
)
async def system_status_backup_callback(
    callback: CallbackQuery,
    context: ApplicationContext,
) -> None:
    """
    Display latest backup status.
    """

    await _render_page(
        callback,
        context,
        formatter=(format_system_backup),
        keyboard=(
            system_status_detail_keyboard(
                refresh_callback=(SYSTEM_STATUS_BACKUP_CALLBACK),
            )
        ),
    )


# =========================================================
# PROJECTS
# =========================================================


@router.callback_query(
    F.data == SYSTEM_STATUS_PROJECTS_CALLBACK,
)
async def system_status_projects_callback(
    callback: CallbackQuery,
    context: ApplicationContext,
) -> None:
    """
    Display project summary.
    """

    await _render_page(
        callback,
        context,
        formatter=(format_system_projects),
        keyboard=(
            system_status_detail_keyboard(
                refresh_callback=(SYSTEM_STATUS_PROJECTS_CALLBACK),
            )
        ),
    )


# =========================================================
# SYSTEM INFORMATION
# =========================================================


@router.callback_query(
    F.data == SYSTEM_STATUS_SYSTEM_CALLBACK,
)
async def system_status_information_callback(
    callback: CallbackQuery,
    context: ApplicationContext,
) -> None:
    """
    Display operating-system information.
    """

    await _render_page(
        callback,
        context,
        formatter=(format_system_information),
        keyboard=(
            system_status_detail_keyboard(
                refresh_callback=(SYSTEM_STATUS_SYSTEM_CALLBACK),
            )
        ),
    )


__all__ = [
    "router",
    "system_status_backup_callback",
    "system_status_callback",
    "system_status_information_callback",
    "system_status_overview_callback",
    "system_status_projects_callback",
    "system_status_refresh_callback",
    "system_status_resources_callback",
    "system_status_services_callback",
]
