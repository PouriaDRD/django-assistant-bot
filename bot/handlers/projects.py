from __future__ import annotations

from pathlib import Path
from typing import Final

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.context import ApplicationContext
from bot.keyboards.projects import (
    project_confirmation_keyboard,
    project_details_keyboard,
    projects_menu_keyboard,
    project_list_keyboard,
    schedule_keyboard,
)

from bot.states.project import ProjectCreationState
from config.models import (
    ProjectConfig,
    ScheduleConfig,
    ScheduleUnit,
)
from services.project_service import (
    ProjectAlreadyExistsError,
    ProjectCreateData,
    ProjectNotFoundError,
    ProjectService,
    ProjectValidationError,
)

router: Final[Router] = Router(name="projects")


# ============================================================
# CONSTANTS
# ============================================================

PROJECT_NAME_MAX_LENGTH: Final[int] = 200


# ============================================================
# SERVICE
# ============================================================


def get_project_service(
    context: ApplicationContext,
) -> ProjectService:
    """
    Create a project service using the application's
    settings manager.
    """
    return ProjectService(
        settings=context.settings,
    )


# ============================================================
# COMMANDS
# ============================================================


@router.message(Command("project"))
async def project_command(
    message: Message,
    state: FSMContext,
    context: ApplicationContext,
) -> None:
    """
    Handle the /project command.

    Supported commands:

    /project
    /project create
    /project list
    """

    command = (message.text or "").strip()

    parts = command.split(
        maxsplit=1,
    )

    if len(parts) == 1:
        await message.answer(
            "📦 <b>مدیریت پروژه‌ها</b>\n"
            "\n"
            "/project create — افزودن پروژه\n"
            "/project list — لیست پروژه‌ها\n"
            "\n"
            "یا از منوی زیر استفاده کنید:",
            reply_markup=projects_menu_keyboard(),
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
        "<code>/project list</code>",
    )


@router.callback_query(
    F.data == "projects",
)
async def projects_menu_callback(
    callback: CallbackQuery,
) -> None:
    await callback.answer()

    if not isinstance(callback.message, Message):
        return

    await callback.message.edit_text(
        "📦 <b>مدیریت پروژه‌ها</b>\n" "\n" "از گزینه‌های زیر استفاده کنید:",
        reply_markup=projects_menu_keyboard(),
    )


# ============================================================
# CREATE PROJECT
# ============================================================


async def start_project_creation(
    message: Message,
    state: FSMContext,
) -> None:
    """
    Start the project creation FSM.
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
    """
    Start project creation from the inline keyboard.
    """

    await state.clear()

    await state.set_state(
        ProjectCreationState.waiting_for_name,
    )

    await callback.answer()

    if not isinstance(callback.message, Message):
        return

    await callback.message.edit_text(
        "➕ <b>افزودن پروژه</b>\n" "\n" "نام پروژه را وارد کنید:",
    )


@router.message(
    ProjectCreationState.waiting_for_name,
)
async def project_name_handler(
    message: Message,
    state: FSMContext,
) -> None:
    """
    Receive and validate project name.
    """

    name = (message.text or "").strip()

    if not name:
        await message.answer(
            "❌ نام پروژه نمی‌تواند خالی باشد.",
        )
        return

    if len(name) > PROJECT_NAME_MAX_LENGTH:
        await message.answer(
            "❌ نام پروژه نمی‌تواند بیشتر از "
            f"{PROJECT_NAME_MAX_LENGTH} کاراکتر باشد.",
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
        "مسیر کامل فایل دیتابیس SQLite را وارد کنید.\n"
        "\n"
        "مثال:\n"
        "<code>/var/www/project/db.sqlite3</code>",
    )


@router.message(
    ProjectCreationState.waiting_for_database_path,
)
async def project_database_handler(
    message: Message,
    state: FSMContext,
) -> None:
    """
    Receive and validate database path.
    """

    database_path = (message.text or "").strip()

    if not database_path:
        await message.answer(
            "❌ مسیر دیتابیس نمی‌تواند خالی باشد.",
        )
        return

    path = Path(
        database_path,
    ).expanduser()

    if not path.is_absolute():
        await message.answer(
            "❌ مسیر باید کامل و Absolute باشد.\n"
            "\n"
            "مثال:\n"
            "<code>/var/www/project/db.sqlite3</code>",
        )
        return

    await state.update_data(
        database_path=str(path),
    )

    await state.set_state(
        ProjectCreationState.waiting_for_media_path,
    )

    await message.answer(
        "📁 <b>Media Path</b>\n"
        "\n"
        "مسیر کامل پوشه Media را وارد کنید.\n"
        "\n"
        "مثال:\n"
        "<code>/var/www/project/media</code>",
    )


@router.message(
    ProjectCreationState.waiting_for_media_path,
)
async def project_media_handler(
    message: Message,
    state: FSMContext,
) -> None:
    """
    Receive and validate media path.
    """

    media_path = (message.text or "").strip()

    if not media_path:
        await message.answer(
            "❌ مسیر Media نمی‌تواند خالی باشد.",
        )
        return

    path = Path(
        media_path,
    ).expanduser()

    if not path.is_absolute():
        await message.answer(
            "❌ مسیر باید کامل و Absolute باشد.",
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
        "Backup این پروژه هر چند وقت یک‌بار انجام شود؟",
        reply_markup=schedule_keyboard(),
    )


# ============================================================
# SCHEDULE
# ============================================================


@router.callback_query(
    ProjectCreationState.waiting_for_schedule,
    F.data.startswith("project:schedule:"),
)
async def project_schedule_handler(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    """
    Receive project backup schedule.
    """

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
        interval = int(interval_raw)
        unit = ScheduleUnit(unit_raw)

        schedule = ScheduleConfig(
            enabled=True,
            interval=interval,
            unit=unit,
        )

    except (TypeError, ValueError):
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

    await state.set_state(
        ProjectCreationState.waiting_for_confirmation,
    )

    data = await state.get_data()

    project_name = data.get("project_name")
    database_path = data.get("database_path")
    media_path = data.get("media_path")

    if (
        not isinstance(project_name, str)
        or not isinstance(database_path, str)
        or not isinstance(media_path, str)
        or not project_name.strip()
        or not database_path.strip()
        or not media_path.strip()
    ):
        await state.clear()

        await callback.answer(
            "اطلاعات پروژه ناقص است.",
            show_alert=True,
        )
        return

    await callback.answer()

    if not isinstance(callback.message, Message):
        return

    await callback.message.edit_text(
        format_project_confirmation(
            name=project_name,
            database_path=database_path,
            media_path=media_path,
            schedule=schedule,
        ),
        reply_markup=project_confirmation_keyboard(),
    )


# ============================================================
# CONFIRM PROJECT
# ============================================================


@router.callback_query(
    ProjectCreationState.waiting_for_confirmation,
    F.data == "project:create:confirm",
)
async def project_create_confirm(
    callback: CallbackQuery,
    state: FSMContext,
    context: ApplicationContext,
) -> None:
    """
    Confirm and persist a new project.
    """

    data = await state.get_data()

    project_name = data.get("project_name")
    database_path = data.get("database_path")
    media_path = data.get("media_path")
    schedule_data = data.get("schedule")

    if not isinstance(project_name, str):
        await callback.answer(
            "نام پروژه نامعتبر است.",
            show_alert=True,
        )
        return

    if not isinstance(database_path, str):
        await callback.answer(
            "مسیر دیتابیس نامعتبر است.",
            show_alert=True,
        )
        return

    if not isinstance(media_path, str):
        await callback.answer(
            "مسیر Media نامعتبر است.",
            show_alert=True,
        )
        return

    if not isinstance(schedule_data, dict):
        await callback.answer(
            "زمان‌بندی پروژه نامعتبر است.",
            show_alert=True,
        )
        return

    try:
        schedule = ScheduleConfig.model_validate(
            schedule_data,
        )

        service = get_project_service(
            context,
        )

        project = service.create_project(
            ProjectCreateData(
                name=project_name,
                database_path=Path(
                    database_path,
                ),
                media_path=Path(
                    media_path,
                ),
                schedule=schedule,
            ),
        )

    except ProjectAlreadyExistsError:
        await callback.answer(
            "پروژه‌ای با این نام وجود دارد.",
            show_alert=True,
        )
        return

    except ProjectValidationError as exc:
        await callback.answer(
            str(exc),
            show_alert=True,
        )
        return

    except ValueError:
        await callback.answer(
            "اطلاعات پروژه نامعتبر است.",
            show_alert=True,
        )
        return

    except Exception:
        await callback.answer(
            "خطایی هنگام ایجاد پروژه رخ داد.",
            show_alert=True,
        )
        return

    await state.clear()

    await callback.answer(
        "پروژه با موفقیت ایجاد شد.",
    )

    if not isinstance(callback.message, Message):
        return

    await callback.message.edit_text(
        format_project_created(
            project,
        ),
        reply_markup=projects_menu_keyboard(),
    )


# ============================================================
# CANCEL CREATE
# ============================================================


@router.callback_query(
    ProjectCreationState.waiting_for_confirmation,
    F.data == "project:create:cancel",
)
async def project_create_cancel(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    """
    Cancel project creation.
    """

    await state.clear()

    await callback.answer(
        "ایجاد پروژه لغو شد.",
    )

    if not isinstance(callback.message, Message):
        return

    await callback.message.edit_text(
        "❌ ایجاد پروژه لغو شد.",
        reply_markup=projects_menu_keyboard(),
    )


# ============================================================
# PROJECT LIST
# ============================================================


@router.callback_query(
    F.data == "project:list",
)
async def project_list_callback(
    callback: CallbackQuery,
    context: ApplicationContext,
) -> None:
    service = get_project_service(context)

    projects = service.list_projects()

    await callback.answer()

    if not isinstance(callback.message, Message):
        return

    if not projects:
        await callback.message.edit_text(
            "📋 <b>پروژه‌ها</b>\n"
            "\n"
            "هنوز هیچ پروژه‌ای ثبت نشده است.\n"
            "\n"
            "برای شروع یک پروژه اضافه کنید.",
            reply_markup=project_list_keyboard(
                projects,
            ),
        )
        return

    await callback.message.edit_text(
        format_project_list(projects),
        reply_markup=project_list_keyboard(
            projects,
        ),
    )


async def send_project_list(
    message: Message,
    context: ApplicationContext,
    *,
    edit: bool = False,
) -> None:
    """
    Send or edit the project list.
    """

    service = get_project_service(
        context,
    )

    projects = service.list_projects()

    text = format_project_list(
        projects,
    )

    if edit:
        await message.edit_text(
            text,
            reply_markup=projects_menu_keyboard(),
        )
        return

    await message.answer(
        text,
        reply_markup=projects_menu_keyboard(),
    )


# ============================================================
# PROJECT DETAILS
# ============================================================


@router.callback_query(
    F.data.startswith("project:view:"),
)
async def project_view_callback(
    callback: CallbackQuery,
    context: ApplicationContext,
) -> None:
    """
    Display project details.
    """

    callback_data = callback.data

    if not callback_data:
        await callback.answer()
        return

    project_id = callback_data.removeprefix(
        "project:view:",
    )

    if not project_id:
        await callback.answer(
            "شناسه پروژه نامعتبر است.",
            show_alert=True,
        )
        return

    service = get_project_service(
        context,
    )

    try:
        project = service.get_project(
            project_id,
        )

    except ProjectNotFoundError:
        await callback.answer(
            "پروژه پیدا نشد.",
            show_alert=True,
        )
        return

    await callback.answer()

    if not isinstance(callback.message, Message):
        return

    await callback.message.edit_text(
        format_project_details(
            project,
        ),
        reply_markup=project_details_keyboard(
            project.id,
            project.enabled,
        ),
    )


# ============================================================
# ENABLE / DISABLE
# ============================================================


@router.callback_query(
    F.data.startswith("project:enable:"),
)
async def project_enable_callback(
    callback: CallbackQuery,
    context: ApplicationContext,
) -> None:
    """
    Enable a project.
    """

    await set_project_status(
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
    """
    Disable a project.
    """

    await set_project_status(
        callback=callback,
        context=context,
        enabled=False,
    )


async def set_project_status(
    callback: CallbackQuery,
    context: ApplicationContext,
    *,
    enabled: bool,
) -> None:
    """
    Update the enabled status of a project.
    """

    callback_data = callback.data

    if not callback_data:
        await callback.answer()
        return

    prefix = "project:enable:" if enabled else "project:disable:"

    project_id = callback_data.removeprefix(
        prefix,
    )

    if not project_id:
        await callback.answer(
            "شناسه پروژه نامعتبر است.",
            show_alert=True,
        )
        return

    service = get_project_service(
        context,
    )

    try:
        project = service.set_enabled(
            project_id=project_id,
            enabled=enabled,
        )

    except ProjectNotFoundError:
        await callback.answer(
            "پروژه پیدا نشد.",
            show_alert=True,
        )
        return

    await callback.answer(
        "پروژه فعال شد." if enabled else "پروژه غیرفعال شد.",
    )

    if not isinstance(callback.message, Message):
        return

    await callback.message.edit_text(
        format_project_details(
            project,
        ),
        reply_markup=project_details_keyboard(
            project.id,
            project.enabled,
        ),
    )


# ============================================================
# DELETE
# ============================================================


@router.callback_query(
    F.data.startswith("project:delete:"),
)
async def project_delete_callback(
    callback: CallbackQuery,
    context: ApplicationContext,
) -> None:
    """
    Delete a project from configuration.
    """

    callback_data = callback.data

    if not callback_data:
        await callback.answer()
        return

    project_id = callback_data.removeprefix(
        "project:delete:",
    )

    if not project_id:
        await callback.answer(
            "شناسه پروژه نامعتبر است.",
            show_alert=True,
        )
        return

    service = get_project_service(
        context,
    )

    try:
        project = service.delete_project(
            project_id,
        )

    except ProjectNotFoundError:
        await callback.answer(
            "پروژه پیدا نشد.",
            show_alert=True,
        )
        return

    await callback.answer(
        "پروژه حذف شد.",
    )

    if not isinstance(callback.message, Message):
        return

    await callback.message.edit_text(
        f"🗑 پروژه <b>{project.name}</b> حذف شد.",
        reply_markup=projects_menu_keyboard(),
    )


# ============================================================
# FORMATTERS
# ============================================================


def format_project_created(
    project: ProjectConfig,
) -> str:
    """
    Format successful project creation message.
    """

    return (
        "✅ <b>پروژه با موفقیت ایجاد شد.</b>\n"
        "\n"
        f"📦 {project.name}\n"
        f"🆔 <code>{project.id}</code>\n"
        "\n"
        "وضعیت: 🟢 فعال"
    )


def format_project_list(
    projects: list[ProjectConfig],
) -> str:
    if not projects:
        return "📋 <b>پروژه‌ها</b>\n" "\n" "هیچ پروژه‌ای ثبت نشده است."

    lines = [
        "📋 <b>پروژه‌های ثبت‌شده</b>",
        "",
    ]

    for index, project in enumerate(
        projects,
        start=1,
    ):
        status = "🟢 فعال" if project.enabled else "🔴 غیرفعال"

        lines.append(f"{index}. <b>{project.name}</b> — {status}")

    lines.extend(
        [
            "",
            "برای مدیریت یک پروژه، روی نام آن بزنید.",
        ]
    )

    return "\n".join(lines)


def format_project_details(
    project: ProjectConfig,
) -> str:
    """
    Format project details.
    """

    status = "🟢 فعال" if project.enabled else "🔴 غیرفعال"

    return (
        f"📦 <b>{project.name}</b>\n"
        "\n"
        f"🆔 <code>{project.id}</code>\n"
        "\n"
        f"وضعیت: {status}\n"
        "\n"
        "🗄 <b>Database</b>\n"
        f"<code>{project.database.path}</code>\n"
        "\n"
        "📁 <b>Media</b>\n"
        f"<code>{project.media.path}</code>\n"
        "\n"
        "⏰ <b>Schedule</b>\n"
        f"{project.schedule.interval} "
        f"{project.schedule.unit.value}"
    )


def format_project_confirmation(
    name: str,
    database_path: str,
    media_path: str,
    schedule: ScheduleConfig,
) -> str:
    """
    Format project creation confirmation.
    """

    return (
        "🔎 <b>بررسی اطلاعات پروژه</b>\n"
        "\n"
        f"📦 نام:\n"
        f"<code>{name}</code>\n"
        "\n"
        f"🗄 Database:\n"
        f"<code>{database_path}</code>\n"
        "\n"
        f"📁 Media:\n"
        f"<code>{media_path}</code>\n"
        "\n"
        "⏰ Schedule:\n"
        f"<code>{schedule.interval} "
        f"{schedule.unit.value}</code>\n"
        "\n"
        "آیا اطلاعات صحیح است؟"
    )
