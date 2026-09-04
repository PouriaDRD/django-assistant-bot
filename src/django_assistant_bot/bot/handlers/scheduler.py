from __future__ import annotations

import logging

from aiogram import (
    F,
    Router,
)
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardMarkup,
    Message,
)
from pydantic import (
    ValidationError,
)

from django_assistant_bot.bot.context import (
    ApplicationContext,
)
from django_assistant_bot.bot.formatters.scheduler import (
    format_project_schedule,
    format_schedule_interval_menu,
    format_schedule_unit_menu,
    format_scheduler_menu,
)
from django_assistant_bot.bot.keyboards.scheduler import (
    SCHEDULER_FILTER_PREFIX,
    SCHEDULER_INTERVAL_PREFIX,
    SCHEDULER_INTERVAL_SET_PREFIX,
    SCHEDULER_MENU_CALLBACK,
    SCHEDULER_PROJECT_PREFIX,
    SCHEDULER_TOGGLE_PREFIX,
    SCHEDULER_UNIT_PREFIX,
    SCHEDULER_UNIT_SET_PREFIX,
    ScheduleFilter,
    ScheduleOrigin,
    project_schedule_keyboard,
    schedule_interval_keyboard,
    schedule_unit_keyboard,
    scheduler_menu_keyboard,
)
from django_assistant_bot.database.models.enums import (
    ScheduleUnit,
)
from django_assistant_bot.schemas.project import (
    ProjectSchema,
    ScheduleUpdateSchema,
)
from django_assistant_bot.services.project import (
    ProjectNotFoundError,
    ProjectPersistenceError,
    ProjectValidationError,
)

logger = logging.getLogger(
    __name__,
)

router = Router(
    name="scheduler.ui",
)


# =========================================================
# CALLBACK PARSING
# =========================================================


def _parse_origin(
    origin_raw: str,
) -> ScheduleOrigin | None:
    """
    Parse scheduler navigation origin.
    """

    if origin_raw == "s":
        return "s"

    if origin_raw == "a":
        return "a"

    if origin_raw == "i":
        return "i"

    if origin_raw == "p":
        return "p"

    return None


def _parse_project_origin(
    payload: str,
) -> (
    tuple[
        str,
        ScheduleOrigin,
    ]
    | None
):
    """
    Parse:
        <project_id>:<origin>
    """

    try:
        project_id, origin_raw = payload.rsplit(
            ":",
            maxsplit=1,
        )

    except ValueError:
        return None

    if not project_id:
        return None

    origin = _parse_origin(origin_raw)

    if origin is None:
        return None

    return (
        project_id,
        origin,
    )


def _parse_project_origin_value(
    payload: str,
) -> (
    tuple[
        str,
        ScheduleOrigin,
        str,
    ]
    | None
):
    """
    Parse:
        <project_id>:<origin>:<value>
    """

    try:
        project_id, origin_raw, value = payload.rsplit(
            ":",
            maxsplit=2,
        )

    except ValueError:
        return None

    if not project_id:
        return None

    if not value:
        return None

    origin = _parse_origin(origin_raw)

    if origin is None:
        return None

    return (
        project_id,
        origin,
        value,
    )


# =========================================================
# FILTERING
# =========================================================


def _filter_projects(
    projects: list[ProjectSchema],
    schedule_filter: ScheduleFilter,
) -> list[ProjectSchema]:
    """
    Filter projects by effective scheduler state.

    Active:
        project enabled
        AND schedule enabled

    Inactive:
        project disabled
        OR schedule disabled
    """

    if schedule_filter == "a":
        return [
            project
            for project in projects
            if (project.enabled and project.schedule.enabled)
        ]

    if schedule_filter == "i":
        return [
            project
            for project in projects
            if not (project.enabled and project.schedule.enabled)
        ]

    return projects


# =========================================================
# MESSAGE
# =========================================================


async def _edit_message(
    callback: CallbackQuery,
    *,
    text: str,
    reply_markup: InlineKeyboardMarkup,
) -> None:
    """
    Safely edit callback message.
    """

    if not isinstance(
        callback.message,
        Message,
    ):
        return

    await callback.message.edit_text(
        text,
        reply_markup=reply_markup,
    )


# =========================================================
# PROJECT SCHEDULE RENDERER
# =========================================================


async def _show_project_schedule(
    callback: CallbackQuery,
    context: ApplicationContext,
    *,
    project_id: str,
    origin: ScheduleOrigin,
) -> None:
    """
    Render schedule-management page for one project.
    """

    try:
        project = context.projects.get_project(project_id)

    except ProjectNotFoundError:
        await callback.answer(
            "پروژه پیدا نشد.",
            show_alert=True,
        )
        return

    except ProjectPersistenceError:
        await callback.answer(
            "خطا در دریافت اطلاعات پروژه.",
            show_alert=True,
        )
        return

    await callback.answer()

    await _edit_message(
        callback,
        text=(format_project_schedule(project)),
        reply_markup=(
            project_schedule_keyboard(
                project,
                origin,
            )
        ),
    )


# =========================================================
# GLOBAL SCHEDULER MENU
# =========================================================


@router.callback_query(
    F.data == SCHEDULER_MENU_CALLBACK,
)
async def scheduler_menu_callback(
    callback: CallbackQuery,
    context: ApplicationContext,
) -> None:
    """
    Show all projects and scheduler states.
    """

    try:
        projects = context.projects.list_projects()

    except ProjectPersistenceError:
        await callback.answer(
            "خطا در دریافت پروژه‌ها.",
            show_alert=True,
        )
        return

    await callback.answer()

    await _edit_message(
        callback,
        text=(
            format_scheduler_menu(
                projects,
                selected_filter="s",
            )
        ),
        reply_markup=(
            scheduler_menu_keyboard(
                projects,
                selected_filter="s",
            )
        ),
    )


# =========================================================
# SCHEDULER FILTER
# =========================================================


@router.callback_query(
    F.data.startswith(SCHEDULER_FILTER_PREFIX),
)
async def scheduler_filter_callback(
    callback: CallbackQuery,
    context: ApplicationContext,
) -> None:
    """
    Filter projects by effective scheduler status.
    """

    callback_data = callback.data

    if not callback_data:
        await callback.answer()
        return

    filter_raw = callback_data.removeprefix(SCHEDULER_FILTER_PREFIX)

    if filter_raw == "a":
        selected_filter: ScheduleFilter = "a"

    elif filter_raw == "i":
        selected_filter = "i"

    else:
        await callback.answer(
            "فیلتر زمان‌بندی نامعتبر است.",
            show_alert=True,
        )
        return

    try:
        projects = context.projects.list_projects()

    except ProjectPersistenceError:
        await callback.answer(
            "خطا در دریافت پروژه‌ها.",
            show_alert=True,
        )
        return

    filtered_projects = _filter_projects(
        projects,
        selected_filter,
    )

    await callback.answer()

    await _edit_message(
        callback,
        text=(
            format_scheduler_menu(
                projects,
                selected_filter=selected_filter,
            )
        ),
        reply_markup=(
            scheduler_menu_keyboard(
                filtered_projects,
                selected_filter=selected_filter,
            )
        ),
    )


# =========================================================
# PROJECT SCHEDULE
# =========================================================


@router.callback_query(
    F.data.startswith(SCHEDULER_PROJECT_PREFIX),
)
async def scheduler_project_callback(
    callback: CallbackQuery,
    context: ApplicationContext,
) -> None:
    """
    Open project schedule-management page.
    """

    callback_data = callback.data

    if not callback_data:
        await callback.answer()
        return

    payload = callback_data.removeprefix(SCHEDULER_PROJECT_PREFIX)

    parsed = _parse_project_origin(payload)

    if parsed is None:
        await callback.answer(
            "اطلاعات زمان‌بندی نامعتبر است.",
            show_alert=True,
        )
        return

    project_id, origin = parsed

    await _show_project_schedule(
        callback,
        context,
        project_id=project_id,
        origin=origin,
    )


# =========================================================
# TOGGLE SCHEDULE
# =========================================================


@router.callback_query(
    F.data.startswith(SCHEDULER_TOGGLE_PREFIX),
)
async def scheduler_toggle_callback(
    callback: CallbackQuery,
    context: ApplicationContext,
) -> None:
    """
    Enable or disable project schedule.
    """

    callback_data = callback.data

    if not callback_data:
        await callback.answer()
        return

    payload = callback_data.removeprefix(SCHEDULER_TOGGLE_PREFIX)

    parsed = _parse_project_origin(payload)

    if parsed is None:
        await callback.answer(
            "اطلاعات زمان‌بندی نامعتبر است.",
            show_alert=True,
        )
        return

    project_id, origin = parsed

    try:
        project = context.projects.get_project(project_id)

        updated = context.projects.set_schedule_enabled(
            project.id,
            not project.schedule.enabled,
        )

    except ProjectNotFoundError:
        await callback.answer(
            "پروژه پیدا نشد.",
            show_alert=True,
        )
        return

    except (
        ProjectPersistenceError,
        ProjectValidationError,
    ):
        await callback.answer(
            "خطا در تغییر وضعیت زمان‌بندی.",
            show_alert=True,
        )
        return

    try:
        context.scheduler.sync_project(updated)

    except Exception:
        logger.exception(
            "Could not synchronize schedule status " "for project %s.",
            updated.id,
        )

    status_text = (
        "زمان‌بندی فعال شد." if updated.schedule.enabled else "زمان‌بندی غیرفعال شد."
    )

    await callback.answer(status_text)

    await _edit_message(
        callback,
        text=(format_project_schedule(updated)),
        reply_markup=(
            project_schedule_keyboard(
                updated,
                origin,
            )
        ),
    )


# =========================================================
# INTERVAL MENU
# =========================================================


@router.callback_query(
    F.data.startswith(SCHEDULER_INTERVAL_PREFIX),
)
async def scheduler_interval_callback(
    callback: CallbackQuery,
    context: ApplicationContext,
) -> None:
    """
    Show interval-selection menu.
    """

    callback_data = callback.data

    if not callback_data:
        await callback.answer()
        return

    payload = callback_data.removeprefix(SCHEDULER_INTERVAL_PREFIX)

    parsed = _parse_project_origin(payload)

    if parsed is None:
        await callback.answer(
            "اطلاعات زمان‌بندی نامعتبر است.",
            show_alert=True,
        )
        return

    project_id, origin = parsed

    try:
        project = context.projects.get_project(project_id)

    except ProjectNotFoundError:
        await callback.answer(
            "پروژه پیدا نشد.",
            show_alert=True,
        )
        return

    except ProjectPersistenceError:
        await callback.answer(
            "خطا در دریافت پروژه.",
            show_alert=True,
        )
        return

    await callback.answer()

    await _edit_message(
        callback,
        text=(format_schedule_interval_menu(project)),
        reply_markup=(
            schedule_interval_keyboard(
                project.id,
                origin,
            )
        ),
    )


# =========================================================
# SET INTERVAL
# =========================================================


@router.callback_query(
    F.data.startswith(SCHEDULER_INTERVAL_SET_PREFIX),
)
async def scheduler_interval_set_callback(
    callback: CallbackQuery,
    context: ApplicationContext,
) -> None:
    """
    Update project schedule interval.
    """

    callback_data = callback.data

    if not callback_data:
        await callback.answer()
        return

    payload = callback_data.removeprefix(SCHEDULER_INTERVAL_SET_PREFIX)

    parsed = _parse_project_origin_value(payload)

    if parsed is None:
        await callback.answer(
            "مقدار زمان‌بندی نامعتبر است.",
            show_alert=True,
        )
        return

    project_id, origin, interval_raw = parsed

    try:
        interval = int(interval_raw)

        schedule_update = ScheduleUpdateSchema(
            interval=interval,
        )

    except (
        ValueError,
        ValidationError,
    ):
        await callback.answer(
            "فاصله زمان‌بندی نامعتبر است.",
            show_alert=True,
        )
        return

    try:
        updated = context.projects.update_schedule(
            project_id,
            schedule_update,
        )

    except ProjectNotFoundError:
        await callback.answer(
            "پروژه پیدا نشد.",
            show_alert=True,
        )
        return

    except (
        ProjectPersistenceError,
        ProjectValidationError,
    ):
        await callback.answer(
            "خطا در تغییر فاصله زمان‌بندی.",
            show_alert=True,
        )
        return

    try:
        context.scheduler.sync_project(updated)

    except Exception:
        logger.exception(
            "Could not synchronize schedule interval " "for project %s.",
            updated.id,
        )

    await callback.answer("فاصله زمان‌بندی تغییر کرد.")

    await _edit_message(
        callback,
        text=(format_project_schedule(updated)),
        reply_markup=(
            project_schedule_keyboard(
                updated,
                origin,
            )
        ),
    )


# =========================================================
# UNIT MENU
# =========================================================


@router.callback_query(
    F.data.startswith(SCHEDULER_UNIT_PREFIX),
)
async def scheduler_unit_callback(
    callback: CallbackQuery,
    context: ApplicationContext,
) -> None:
    """
    Show schedule-unit selector.
    """

    callback_data = callback.data

    if not callback_data:
        await callback.answer()
        return

    payload = callback_data.removeprefix(SCHEDULER_UNIT_PREFIX)

    parsed = _parse_project_origin(payload)

    if parsed is None:
        await callback.answer(
            "اطلاعات زمان‌بندی نامعتبر است.",
            show_alert=True,
        )
        return

    project_id, origin = parsed

    try:
        project = context.projects.get_project(project_id)

    except ProjectNotFoundError:
        await callback.answer(
            "پروژه پیدا نشد.",
            show_alert=True,
        )
        return

    except ProjectPersistenceError:
        await callback.answer(
            "خطا در دریافت پروژه.",
            show_alert=True,
        )
        return

    await callback.answer()

    await _edit_message(
        callback,
        text=(format_schedule_unit_menu(project)),
        reply_markup=(
            schedule_unit_keyboard(
                project.id,
                origin,
            )
        ),
    )


# =========================================================
# SET UNIT
# =========================================================


@router.callback_query(
    F.data.startswith(SCHEDULER_UNIT_SET_PREFIX),
)
async def scheduler_unit_set_callback(
    callback: CallbackQuery,
    context: ApplicationContext,
) -> None:
    """
    Update project schedule unit.
    """

    callback_data = callback.data

    if not callback_data:
        await callback.answer()
        return

    payload = callback_data.removeprefix(SCHEDULER_UNIT_SET_PREFIX)

    parsed = _parse_project_origin_value(payload)

    if parsed is None:
        await callback.answer(
            "واحد زمان‌بندی نامعتبر است.",
            show_alert=True,
        )
        return

    project_id, origin, unit_raw = parsed

    try:
        unit = ScheduleUnit(unit_raw)

        schedule_update = ScheduleUpdateSchema(
            unit=unit,
        )

    except (
        ValueError,
        ValidationError,
    ):
        await callback.answer(
            "واحد زمان‌بندی نامعتبر است.",
            show_alert=True,
        )
        return

    try:
        updated = context.projects.update_schedule(
            project_id,
            schedule_update,
        )

    except ProjectNotFoundError:
        await callback.answer(
            "پروژه پیدا نشد.",
            show_alert=True,
        )
        return

    except (
        ProjectPersistenceError,
        ProjectValidationError,
    ):
        await callback.answer(
            "خطا در تغییر واحد زمان‌بندی.",
            show_alert=True,
        )
        return

    try:
        context.scheduler.sync_project(updated)

    except Exception:
        logger.exception(
            "Could not synchronize schedule unit " "for project %s.",
            updated.id,
        )

    await callback.answer("واحد زمان‌بندی تغییر کرد.")

    await _edit_message(
        callback,
        text=(format_project_schedule(updated)),
        reply_markup=(
            project_schedule_keyboard(
                updated,
                origin,
            )
        ),
    )


__all__ = [
    "router",
]
