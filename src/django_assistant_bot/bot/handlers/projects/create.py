from __future__ import annotations

import logging
from html import escape
from pathlib import Path
from typing import Final

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    Message,
)
from pydantic import ValidationError

from django_assistant_bot.bot.context import (
    ApplicationContext,
)
from django_assistant_bot.bot.formatters.project import (
    format_project_confirmation,
    format_project_created,
)
from django_assistant_bot.bot.keyboards.projects import (
    project_confirmation_keyboard,
    projects_menu_keyboard,
    schedule_keyboard,
)
from django_assistant_bot.bot.states.project import (
    ProjectCreationState,
)
from django_assistant_bot.database.models.enums import (
    DatabaseType,
    ScheduleUnit,
)
from django_assistant_bot.schemas.project import (
    DatabaseSchema,
    MediaSchema,
    ProjectCreateSchema,
    ScheduleSchema,
)
from django_assistant_bot.services.project import (
    ProjectAlreadyExistsError,
    ProjectPersistenceError,
    ProjectValidationError,
)

# =========================================================
# ROUTER
# =========================================================


router = Router(
    name="projects.create",
)


# =========================================================
# LOGGER
# =========================================================


logger = logging.getLogger(
    __name__,
)


# =========================================================
# CONSTANTS
# =========================================================


PROJECT_NAME_MAX_LENGTH: Final[int] = 200


# =========================================================
# START CREATION
# =========================================================


async def start_project_creation(
    *,
    message: Message,
    state: FSMContext,
) -> None:
    """
    Start the project creation flow.
    """

    await state.clear()

    await state.set_state(
        ProjectCreationState.waiting_for_name,
    )

    await message.answer(
        "➕ <b>افزودن پروژه</b>\n" "\n" "نام پروژه را وارد کنید:",
    )


@router.callback_query(
    F.data == "project:create",
)
async def project_create_callback(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    await state.clear()

    await state.set_state(
        ProjectCreationState.waiting_for_name,
    )

    await callback.answer()

    if not isinstance(
        callback.message,
        Message,
    ):
        return

    await callback.message.edit_text(
        "➕ <b>افزودن پروژه</b>\n" "\n" "نام پروژه را وارد کنید:",
    )


# =========================================================
# PROJECT NAME
# =========================================================


@router.message(
    ProjectCreationState.waiting_for_name,
)
async def project_name_handler(
    message: Message,
    state: FSMContext,
) -> None:
    name = (message.text or "").strip()

    if not name:
        await message.answer("❌ نام پروژه نمی‌تواند خالی باشد.")
        return

    if len(name) > PROJECT_NAME_MAX_LENGTH:
        await message.answer(
            "❌ نام پروژه نمی‌تواند بیشتر از "
            f"{PROJECT_NAME_MAX_LENGTH} "
            "کاراکتر باشد."
        )
        return

    await state.update_data(
        project_name=name,
    )

    await state.set_state(
        ProjectCreationState.waiting_for_database_path,
    )

    await message.answer(
        "🗄 <b>Database Path</b>\n"
        "\n"
        "مسیر کامل فایل دیتابیس SQLite "
        "را وارد کنید.\n"
        "\n"
        "مثال:\n"
        "<code>/var/www/project/db.sqlite3</code>"
    )


# =========================================================
# DATABASE PATH
# =========================================================


@router.message(
    ProjectCreationState.waiting_for_database_path,
)
async def project_database_handler(
    message: Message,
    state: FSMContext,
) -> None:
    raw_path = (message.text or "").strip()

    if not raw_path:
        await message.answer("❌ مسیر دیتابیس نمی‌تواند خالی باشد.")
        return

    path = Path(raw_path).expanduser()

    if not path.is_absolute():
        await message.answer("❌ مسیر دیتابیس باید کامل و Absolute باشد.")
        return

    # Only escape the path used for Telegram HTML output.
    # The real filesystem path remains unchanged.
    safe_path = escape(str(path))

    if not path.exists():
        await message.answer(
            "❌ <b>فایل دیتابیس پیدا نشد.</b>\n"
            "\n"
            "مسیر واردشده:\n"
            f"<code>{safe_path}</code>\n"
            "\n"
            "مسیر صحیح فایل SQLite را دوباره وارد کنید."
        )
        return

    if not path.is_file():
        await message.answer(
            "❌ <b>مسیر دیتابیس معتبر نیست.</b>\n"
            "\n"
            "مسیر واردشده به فایل اشاره نمی‌کند:\n"
            f"<code>{safe_path}</code>\n"
            "\n"
            "مسیر کامل فایل SQLite را وارد کنید."
        )
        return

    await state.update_data(
        database_path=str(path),
    )

    await state.set_state(
        ProjectCreationState.waiting_for_media_path,
    )

    await message.answer(
        "📁 <b>Media Path</b>\n" "\n" "مسیر کامل پوشه Media را وارد کنید."
    )


# =========================================================
# MEDIA PATH
# =========================================================


@router.message(
    ProjectCreationState.waiting_for_media_path,
)
async def project_media_handler(
    message: Message,
    state: FSMContext,
) -> None:
    raw_path = (message.text or "").strip()

    if not raw_path:
        await message.answer("❌ مسیر Media نمی‌تواند خالی باشد.")
        return

    path = Path(raw_path).expanduser()

    if not path.is_absolute():
        await message.answer("❌ مسیر Media باید کامل و Absolute باشد.")
        return

    # Only escape the path used for Telegram HTML output.
    # The real filesystem path remains unchanged.
    safe_path = escape(str(path))

    if not path.exists():
        await message.answer(
            "❌ <b>پوشه Media پیدا نشد.</b>\n"
            "\n"
            "مسیر واردشده:\n"
            f"<code>{safe_path}</code>\n"
            "\n"
            "مسیر صحیح پوشه Media را دوباره وارد کنید."
        )
        return

    if not path.is_dir():
        await message.answer(
            "❌ <b>مسیر Media معتبر نیست.</b>\n"
            "\n"
            "مسیر واردشده به پوشه اشاره نمی‌کند:\n"
            f"<code>{safe_path}</code>\n"
            "\n"
            "مسیر کامل پوشه Media را وارد کنید."
        )
        return

    await state.update_data(
        media_path=str(path),
    )

    await state.set_state(
        ProjectCreationState.waiting_for_schedule,
    )

    await message.answer(
        "⏰ <b>زمان‌بندی Backup</b>\n"
        "\n"
        "Backup این پروژه هر چند وقت "
        "یک‌بار انجام شود؟",
        reply_markup=schedule_keyboard(),
    )


# =========================================================
# SCHEDULE
# =========================================================


@router.callback_query(
    ProjectCreationState.waiting_for_schedule,
    F.data.startswith("project:schedule:"),
)
async def project_schedule_handler(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    callback_data = callback.data

    if not callback_data:
        await callback.answer()
        return

    parts = callback_data.split(":")

    if len(parts) != 4:
        await callback.answer(
            "گزینه نامعتبر است.",
            show_alert=True,
        )
        return

    _, _, interval_raw, unit_raw = parts

    try:
        schedule = ScheduleSchema(
            enabled=True,
            interval=int(interval_raw),
            unit=ScheduleUnit(unit_raw),
        )

    except (
        ValueError,
        ValidationError,
    ):
        await callback.answer(
            "زمان‌بندی نامعتبر است.",
            show_alert=True,
        )
        return

    await state.update_data(
        schedule=schedule.model_dump(
            mode="json",
        ),
    )

    data = await state.get_data()

    project_name = data.get("project_name")

    database_path = data.get("database_path")

    media_path = data.get("media_path")

    if (
        not isinstance(
            project_name,
            str,
        )
        or not isinstance(
            database_path,
            str,
        )
        or not isinstance(
            media_path,
            str,
        )
    ):
        await state.clear()

        await callback.answer(
            "اطلاعات پروژه ناقص است.",
            show_alert=True,
        )
        return

    await state.set_state(
        ProjectCreationState.waiting_for_confirmation,
    )

    await callback.answer()

    if not isinstance(
        callback.message,
        Message,
    ):
        return

    await callback.message.edit_text(
        format_project_confirmation(
            name=project_name,
            database_path=database_path,
            media_path=media_path,
            schedule=schedule,
        ),
        reply_markup=(project_confirmation_keyboard()),
    )


# =========================================================
# CONFIRM CREATION
# =========================================================


@router.callback_query(
    ProjectCreationState.waiting_for_confirmation,
    F.data == "project:create:confirm",
)
async def project_create_confirm(
    callback: CallbackQuery,
    state: FSMContext,
    context: ApplicationContext,
) -> None:
    data = await state.get_data()

    project_name = data.get("project_name")

    database_path = data.get("database_path")

    media_path = data.get("media_path")

    schedule_data = data.get("schedule")

    if not isinstance(
        project_name,
        str,
    ):
        await callback.answer(
            "نام پروژه نامعتبر است.",
            show_alert=True,
        )
        return

    if not isinstance(
        database_path,
        str,
    ):
        await callback.answer(
            "مسیر دیتابیس نامعتبر است.",
            show_alert=True,
        )
        return

    if not isinstance(
        media_path,
        str,
    ):
        await callback.answer(
            "مسیر Media نامعتبر است.",
            show_alert=True,
        )
        return

    if not isinstance(
        schedule_data,
        dict,
    ):
        await callback.answer(
            "زمان‌بندی پروژه نامعتبر است.",
            show_alert=True,
        )
        return

    try:
        schedule = ScheduleSchema.model_validate(schedule_data)

        project = context.projects.create_project(
            ProjectCreateSchema(
                name=project_name,
                database=DatabaseSchema(
                    type=DatabaseType.SQLITE,
                    path=Path(database_path),
                ),
                media=MediaSchema(
                    enabled=True,
                    path=Path(media_path),
                ),
                schedule=schedule,
            )
        )

    except ProjectAlreadyExistsError:
        await callback.answer(
            "پروژه‌ای با این نام وجود دارد.",
            show_alert=True,
        )
        return

    except (
        ProjectValidationError,
        ValidationError,
    ) as exc:
        await callback.answer(
            str(exc),
            show_alert=True,
        )
        return

    except ProjectPersistenceError:
        logger.exception("Could not create project.")

        await callback.answer(
            "خطایی هنگام ذخیره پروژه رخ داد.",
            show_alert=True,
        )
        return

    # -----------------------------------------------------
    # SCHEDULER SYNC
    # -----------------------------------------------------

    try:
        context.scheduler.sync_project(
            project,
        )

    except Exception:
        logger.exception(
            "Project %s was created but " "scheduler sync failed.",
            project.id,
        )

    await state.clear()

    await callback.answer("پروژه با موفقیت ایجاد شد.")

    if not isinstance(
        callback.message,
        Message,
    ):
        return

    await callback.message.edit_text(
        format_project_created(project),
        reply_markup=(projects_menu_keyboard()),
    )


# =========================================================
# CANCEL CREATION
# =========================================================


@router.callback_query(
    ProjectCreationState.waiting_for_confirmation,
    F.data == "project:create:cancel",
)
async def project_create_cancel(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    await state.clear()

    await callback.answer("ایجاد پروژه لغو شد.")

    if not isinstance(
        callback.message,
        Message,
    ):
        return

    await callback.message.edit_text(
        "❌ ایجاد پروژه لغو شد.",
        reply_markup=(projects_menu_keyboard()),
    )


__all__ = [
    "router",
    "start_project_creation",
]
