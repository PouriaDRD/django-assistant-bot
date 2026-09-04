from __future__ import annotations

import asyncio

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
from django_assistant_bot.bot.formatters.backup_history import (
    format_backup_history_all,
    format_backup_history_details,
    format_backup_history_list,
    format_backup_history_menu,
)
from django_assistant_bot.bot.keyboards.backup_history import (
    HISTORY_ALL_PREFIX,
    HISTORY_DETAIL_PREFIX,
    HISTORY_PROJECT_PREFIX,
    build_backup_history_all_keyboard,
    build_backup_history_detail_keyboard,
    build_backup_history_list_keyboard,
    build_backup_history_projects_keyboard,
)
from django_assistant_bot.services.backup import (
    BackupHistoryNotFoundError,
    BackupHistoryPersistenceError,
    BackupHistoryValidationError,
)
from django_assistant_bot.services.project import (
    ProjectNotFoundError,
    ProjectPersistenceError,
)

router = Router(
    name="backups.history",
)


PAGE_SIZE = 5


# =========================================================
# HISTORY MENU
# =========================================================


@router.callback_query(
    F.data == "backup:history",
)
async def backup_history_menu_callback(
    callback: CallbackQuery,
    context: ApplicationContext,
) -> None:
    """
    Display backup history navigation page.
    """

    try:
        projects = await asyncio.to_thread(
            context.projects.list_projects,
        )

    except ProjectPersistenceError:
        await callback.answer(
            "دریافت پروژه‌ها ناموفق بود.",
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
        format_backup_history_menu(),
        reply_markup=(
            build_backup_history_projects_keyboard(
                projects,
            )
        ),
    )


# =========================================================
# ALL HISTORY
# =========================================================


@router.callback_query(
    F.data.startswith(HISTORY_ALL_PREFIX),
)
async def backup_history_all_callback(
    callback: CallbackQuery,
    context: ApplicationContext,
) -> None:
    """
    Display paginated backup history for all projects.
    """

    data = callback.data

    if not data:
        await callback.answer()

        return

    page_raw = data.removeprefix(HISTORY_ALL_PREFIX)

    try:
        page = int(page_raw)

    except (
        TypeError,
        ValueError,
    ):
        await callback.answer(
            "اطلاعات صفحه نامعتبر است.",
            show_alert=True,
        )

        return

    if page < 0:
        await callback.answer(
            "شماره صفحه نامعتبر است.",
            show_alert=True,
        )

        return

    offset = page * PAGE_SIZE

    try:
        histories = await asyncio.to_thread(
            context.backup_history.list_all,
            limit=PAGE_SIZE + 1,
            offset=offset,
        )

        projects = await asyncio.to_thread(
            context.projects.list_projects,
        )

    except (
        BackupHistoryValidationError,
        BackupHistoryPersistenceError,
    ):
        await callback.answer(
            "دریافت تاریخچه بکاپ ناموفق بود.",
            show_alert=True,
        )

        return

    except ProjectPersistenceError:
        await callback.answer(
            "دریافت اطلاعات پروژه‌ها ناموفق بود.",
            show_alert=True,
        )

        return

    await callback.answer()

    if not isinstance(
        callback.message,
        Message,
    ):
        return

    has_next = len(histories) > PAGE_SIZE

    visible_histories = histories[:PAGE_SIZE]

    project_names = {project.id: project.name for project in projects}

    await callback.message.edit_text(
        format_backup_history_all(
            histories=(visible_histories),
            project_names=(project_names),
            page=page,
        ),
        reply_markup=(
            build_backup_history_all_keyboard(
                histories=(visible_histories),
                page=page,
                has_next=has_next,
            )
        ),
    )


# =========================================================
# PROJECT HISTORY
# =========================================================


@router.callback_query(
    F.data.startswith(HISTORY_PROJECT_PREFIX),
)
async def backup_history_project_callback(
    callback: CallbackQuery,
    context: ApplicationContext,
) -> None:
    """
    Display paginated backup history for one project.
    """

    data = callback.data

    if not data:
        await callback.answer()

        return

    payload = data.removeprefix(HISTORY_PROJECT_PREFIX)

    try:
        project_id, page_raw = payload.rsplit(
            ":",
            maxsplit=1,
        )

        if not project_id:
            raise ValueError

        page = int(page_raw)

    except (
        TypeError,
        ValueError,
    ):
        await callback.answer(
            "اطلاعات صفحه نامعتبر است.",
            show_alert=True,
        )

        return

    if page < 0:
        await callback.answer(
            "شماره صفحه نامعتبر است.",
            show_alert=True,
        )

        return

    try:
        project = await asyncio.to_thread(
            context.projects.get_project,
            project_id,
        )

        offset = page * PAGE_SIZE

        histories = await asyncio.to_thread(
            context.backup_history.list_for_project,
            project.id,
            limit=PAGE_SIZE + 1,
            offset=offset,
        )

    except ProjectNotFoundError:
        await callback.answer(
            "پروژه پیدا نشد.",
            show_alert=True,
        )

        return

    except ProjectPersistenceError:
        await callback.answer(
            "دریافت پروژه ناموفق بود.",
            show_alert=True,
        )

        return

    except (
        BackupHistoryValidationError,
        BackupHistoryPersistenceError,
    ):
        await callback.answer(
            "دریافت تاریخچه بکاپ ناموفق بود.",
            show_alert=True,
        )

        return

    await callback.answer()

    if not isinstance(
        callback.message,
        Message,
    ):
        return

    has_next = len(histories) > PAGE_SIZE

    visible_histories = histories[:PAGE_SIZE]

    await callback.message.edit_text(
        format_backup_history_list(
            project_name=(project.name),
            histories=(visible_histories),
            page=page,
        ),
        reply_markup=(
            build_backup_history_list_keyboard(
                project_id=project.id,
                histories=(visible_histories),
                page=page,
                has_next=has_next,
            )
        ),
    )


# =========================================================
# HISTORY DETAILS
# =========================================================


@router.callback_query(
    F.data.startswith(HISTORY_DETAIL_PREFIX),
)
async def backup_history_detail_callback(
    callback: CallbackQuery,
    context: ApplicationContext,
) -> None:
    """
    Display detailed information for one backup.

    Callback format:

        bh:d:<history_id>:<origin>:<page>

    origin:
        a = all history
        p = project history

    Legacy callback format is also supported:

        bh:d:<history_id>:<page>

    Legacy callbacks default to project history.
    """

    data = callback.data

    if not data:
        await callback.answer()

        return

    payload = data.removeprefix(HISTORY_DETAIL_PREFIX)

    try:
        parts = payload.rsplit(
            ":",
            maxsplit=2,
        )

        if len(parts) == 2:
            history_id, page_raw = parts

            origin = "p"

        elif len(parts) == 3:
            (
                history_id,
                origin,
                page_raw,
            ) = parts

        else:
            raise ValueError

        if not history_id:
            raise ValueError

        if origin not in {
            "a",
            "p",
        }:
            raise ValueError

        page = int(page_raw)

    except (
        TypeError,
        ValueError,
    ):
        await callback.answer(
            "اطلاعات بکاپ نامعتبر است.",
            show_alert=True,
        )

        return

    if page < 0:
        await callback.answer(
            "شماره صفحه نامعتبر است.",
            show_alert=True,
        )

        return

    try:
        history = await asyncio.to_thread(
            context.backup_history.get_history,
            history_id,
        )

        try:
            project = await asyncio.to_thread(
                context.projects.get_project,
                history.project_id,
            )

            project_name = project.name

        except ProjectNotFoundError:
            project_name = history.project_id

    except BackupHistoryNotFoundError:
        await callback.answer(
            "تاریخچه بکاپ پیدا نشد.",
            show_alert=True,
        )

        return

    except (
        BackupHistoryValidationError,
        BackupHistoryPersistenceError,
    ):
        await callback.answer(
            "دریافت جزئیات بکاپ ناموفق بود.",
            show_alert=True,
        )

        return

    except ProjectPersistenceError:
        await callback.answer(
            "دریافت اطلاعات پروژه ناموفق بود.",
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
        format_backup_history_details(
            history,
            project_name=(project_name),
        ),
        reply_markup=(
            build_backup_history_detail_keyboard(
                project_id=(history.project_id),
                page=page,
                origin=origin,
            )
        ),
    )


__all__ = [
    "PAGE_SIZE",
    "backup_history_all_callback",
    "backup_history_detail_callback",
    "backup_history_menu_callback",
    "backup_history_project_callback",
    "router",
]
