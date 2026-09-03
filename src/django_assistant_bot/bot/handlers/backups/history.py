from __future__ import annotations

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
    format_backup_history_details,
    format_backup_history_list,
    format_backup_history_menu,
)
from django_assistant_bot.bot.keyboards.backup_history import (
    HISTORY_DETAIL_PREFIX,
    HISTORY_PROJECT_PREFIX,
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
)

router = Router(
    name="backups.history",
)


PAGE_SIZE = 5


# =========================================================
# HISTORY PROJECT SELECTOR
# =========================================================


@router.callback_query(
    F.data == "backup:history",
)
async def backup_history_menu_callback(
    callback: CallbackQuery,
    context: ApplicationContext,
) -> None:
    """
    Display project selector for backup history.
    """

    await callback.answer()

    if not isinstance(
        callback.message,
        Message,
    ):
        return

    projects = context.projects.list_projects()

    await callback.message.edit_text(
        format_backup_history_menu(),
        reply_markup=(
            build_backup_history_projects_keyboard(
                projects,
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
    Display paginated backup history for a project.
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
        ValueError,
        TypeError,
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
        project = context.projects.get_project(
            project_id,
        )

        offset = page * PAGE_SIZE

        histories = context.backup_history.list_for_project(
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
            project_name=project.name,
            histories=visible_histories,
            page=page,
        ),
        reply_markup=(
            build_backup_history_list_keyboard(
                project_id=project.id,
                histories=visible_histories,
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
    Display detailed information about one backup.

    The callback contains only history_id and page.

    project_id is resolved from the history record itself
    to keep callback_data below Telegram's 64-byte limit.
    """

    data = callback.data

    if not data:
        await callback.answer()

        return

    payload = data.removeprefix(HISTORY_DETAIL_PREFIX)

    try:
        history_id, page_raw = payload.rsplit(
            ":",
            maxsplit=1,
        )

        if not history_id:
            raise ValueError

        page = int(page_raw)

    except (
        ValueError,
        TypeError,
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
        history = context.backup_history.get_history(
            history_id,
        )

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

    await callback.answer()

    if not isinstance(
        callback.message,
        Message,
    ):
        return

    await callback.message.edit_text(
        format_backup_history_details(
            history,
        ),
        reply_markup=(
            build_backup_history_detail_keyboard(
                project_id=history.project_id,
                page=page,
            )
        ),
    )
