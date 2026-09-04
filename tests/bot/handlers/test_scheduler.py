from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import (
    AsyncMock,
    Mock,
)

import pytest
from aiogram.types import (
    Message,
)

from django_assistant_bot.bot.handlers.scheduler import (
    scheduler_interval_callback,
    scheduler_interval_set_callback,
    scheduler_menu_callback,
    scheduler_project_callback,
    scheduler_toggle_callback,
    scheduler_unit_callback,
    scheduler_unit_set_callback,
)
from django_assistant_bot.database.models.enums import (
    DatabaseType,
    ScheduleUnit,
)
from django_assistant_bot.schemas.project import (
    DatabaseSchema,
    MediaSchema,
    ProjectSchema,
    ScheduleSchema,
    ScheduleUpdateSchema,
)
from django_assistant_bot.services.project import (
    ProjectNotFoundError,
    ProjectPersistenceError,
)

# =========================================================
# BUILDERS
# =========================================================


def build_project(
    tmp_path: Path,
    *,
    project_id: str = "project-1",
    name: str = "Test Project",
    enabled: bool = True,
    schedule_enabled: bool = True,
    interval: int = 5,
    unit: ScheduleUnit = ScheduleUnit.MINUTES,
) -> ProjectSchema:
    return ProjectSchema(
        id=project_id,
        name=name,
        enabled=enabled,
        database=DatabaseSchema(
            type=DatabaseType.SQLITE,
            path=(tmp_path / "db.sqlite3"),
        ),
        media=MediaSchema(
            enabled=False,
            path=(tmp_path / "media"),
        ),
        schedule=ScheduleSchema(
            enabled=schedule_enabled,
            interval=interval,
            unit=unit,
        ),
    )


def build_message() -> Message:
    message = Mock(
        spec=Message,
    )

    message.edit_text = AsyncMock()

    return message


def build_callback(
    *,
    data: str | None,
) -> SimpleNamespace:
    return SimpleNamespace(
        data=data,
        answer=AsyncMock(),
        message=build_message(),
    )


def build_context(
    *,
    projects: list[ProjectSchema] | None = None,
    project: ProjectSchema | None = None,
    updated: ProjectSchema | None = None,
    list_error: Exception | None = None,
    project_error: Exception | None = None,
    update_error: Exception | None = None,
    scheduler_error: Exception | None = None,
) -> SimpleNamespace:
    project_service = Mock()

    if list_error is not None:
        project_service.list_projects.side_effect = list_error
    else:
        project_service.list_projects.return_value = (
            projects if projects is not None else []
        )

    if project_error is not None:
        project_service.get_project.side_effect = project_error
    else:
        project_service.get_project.return_value = project

    if update_error is not None:
        project_service.update_schedule.side_effect = update_error

        project_service.set_schedule_enabled.side_effect = update_error

    else:
        project_service.update_schedule.return_value = updated

        project_service.set_schedule_enabled.return_value = updated

    scheduler = Mock()

    if scheduler_error is not None:
        scheduler.sync_project.side_effect = scheduler_error

    return SimpleNamespace(
        projects=project_service,
        scheduler=scheduler,
    )


# =========================================================
# GLOBAL MENU
# =========================================================


@pytest.mark.asyncio
async def test_scheduler_menu_lists_projects(
    tmp_path: Path,
) -> None:
    project = build_project(
        tmp_path,
    )

    callback = build_callback(
        data="scheduler",
    )

    context = build_context(
        projects=[
            project,
        ],
    )

    await scheduler_menu_callback(
        callback,
        context,
    )

    context.projects.list_projects.assert_called_once_with()

    callback.answer.assert_awaited_once_with()

    callback.message.edit_text.assert_awaited_once()

    call = callback.message.edit_text.await_args

    text = call.args[0]

    assert "مدیریت زمان‌بندی بکاپ‌ها" in text

    keyboard = call.kwargs["reply_markup"]

    callback_data = [
        button.callback_data for row in keyboard.inline_keyboard for button in row
    ]

    assert f"sc:p:{project.id}:s" in callback_data


@pytest.mark.asyncio
async def test_scheduler_menu_persistence_failure() -> None:
    callback = build_callback(
        data="scheduler",
    )

    context = build_context(
        list_error=ProjectPersistenceError("database error"),
    )

    await scheduler_menu_callback(
        callback,
        context,
    )

    callback.answer.assert_awaited_once_with(
        "خطا در دریافت پروژه‌ها.",
        show_alert=True,
    )

    callback.message.edit_text.assert_not_awaited()


# =========================================================
# PROJECT PAGE
# =========================================================


@pytest.mark.asyncio
async def test_scheduler_project_from_global_menu(
    tmp_path: Path,
) -> None:
    project = build_project(
        tmp_path,
    )

    callback = build_callback(
        data=(f"sc:p:{project.id}:s"),
    )

    context = build_context(
        project=project,
    )

    await scheduler_project_callback(
        callback,
        context,
    )

    context.projects.get_project.assert_called_once_with(
        project.id,
    )

    call = callback.message.edit_text.await_args

    assert "زمان‌بندی بکاپ" in call.args[0]

    keyboard = call.kwargs["reply_markup"]

    callback_data = [
        button.callback_data for row in keyboard.inline_keyboard for button in row
    ]

    assert "scheduler" in callback_data


@pytest.mark.asyncio
async def test_scheduler_project_from_project_details(
    tmp_path: Path,
) -> None:
    project = build_project(
        tmp_path,
    )

    callback = build_callback(
        data=(f"sc:p:{project.id}:p"),
    )

    context = build_context(
        project=project,
    )

    await scheduler_project_callback(
        callback,
        context,
    )

    call = callback.message.edit_text.await_args

    keyboard = call.kwargs["reply_markup"]

    callback_data = [
        button.callback_data for row in keyboard.inline_keyboard for button in row
    ]

    assert f"project:view:{project.id}" in callback_data


@pytest.mark.asyncio
async def test_scheduler_project_not_found() -> None:
    callback = build_callback(
        data="sc:p:project-1:s",
    )

    context = build_context(
        project_error=ProjectNotFoundError("not found"),
    )

    await scheduler_project_callback(
        callback,
        context,
    )

    callback.answer.assert_awaited_once_with(
        "پروژه پیدا نشد.",
        show_alert=True,
    )

    callback.message.edit_text.assert_not_awaited()


# =========================================================
# TOGGLE
# =========================================================


@pytest.mark.asyncio
async def test_scheduler_toggle_disables_schedule(
    tmp_path: Path,
) -> None:
    project = build_project(
        tmp_path,
        schedule_enabled=True,
    )

    updated = build_project(
        tmp_path,
        schedule_enabled=False,
    )

    callback = build_callback(
        data=(f"sc:t:{project.id}:s"),
    )

    context = build_context(
        project=project,
        updated=updated,
    )

    await scheduler_toggle_callback(
        callback,
        context,
    )

    context.projects.get_project.assert_called_once_with(
        project.id,
    )

    context.projects.set_schedule_enabled.assert_called_once_with(
        project.id,
        False,
    )

    context.scheduler.sync_project.assert_called_once_with(updated)

    callback.answer.assert_awaited_once_with("زمان‌بندی غیرفعال شد.")

    callback.message.edit_text.assert_awaited_once()


@pytest.mark.asyncio
async def test_scheduler_toggle_enables_schedule(
    tmp_path: Path,
) -> None:
    project = build_project(
        tmp_path,
        schedule_enabled=False,
    )

    updated = build_project(
        tmp_path,
        schedule_enabled=True,
    )

    callback = build_callback(
        data=(f"sc:t:{project.id}:p"),
    )

    context = build_context(
        project=project,
        updated=updated,
    )

    await scheduler_toggle_callback(
        callback,
        context,
    )

    context.projects.set_schedule_enabled.assert_called_once_with(
        project.id,
        True,
    )

    context.scheduler.sync_project.assert_called_once_with(updated)

    callback.answer.assert_awaited_once_with("زمان‌بندی فعال شد.")


@pytest.mark.asyncio
async def test_scheduler_toggle_survives_scheduler_failure(
    tmp_path: Path,
) -> None:
    project = build_project(
        tmp_path,
        schedule_enabled=True,
    )

    updated = build_project(
        tmp_path,
        schedule_enabled=False,
    )

    callback = build_callback(
        data=(f"sc:t:{project.id}:s"),
    )

    context = build_context(
        project=project,
        updated=updated,
        scheduler_error=RuntimeError("scheduler failed"),
    )

    await scheduler_toggle_callback(
        callback,
        context,
    )

    context.projects.set_schedule_enabled.assert_called_once_with(
        project.id,
        False,
    )

    context.scheduler.sync_project.assert_called_once_with(updated)

    # Persisted schedule mutation remains successful.
    callback.answer.assert_awaited_once_with("زمان‌بندی غیرفعال شد.")

    callback.message.edit_text.assert_awaited_once()


# =========================================================
# INTERVAL MENU
# =========================================================


@pytest.mark.asyncio
async def test_scheduler_interval_menu(
    tmp_path: Path,
) -> None:
    project = build_project(
        tmp_path,
        interval=5,
    )

    callback = build_callback(
        data=(f"sc:i:{project.id}:s"),
    )

    context = build_context(
        project=project,
    )

    await scheduler_interval_callback(
        callback,
        context,
    )

    context.projects.get_project.assert_called_once_with(
        project.id,
    )

    call = callback.message.edit_text.await_args

    assert "تغییر فاصله اجرا" in call.args[0]

    assert "5 دقیقه" in call.args[0]


# =========================================================
# SET INTERVAL
# =========================================================


@pytest.mark.asyncio
async def test_scheduler_interval_update(
    tmp_path: Path,
) -> None:
    project = build_project(
        tmp_path,
        interval=5,
    )

    updated = build_project(
        tmp_path,
        interval=15,
    )

    callback = build_callback(
        data=(f"sc:is:{project.id}:s:15"),
    )

    context = build_context(
        updated=updated,
    )

    await scheduler_interval_set_callback(
        callback,
        context,
    )

    context.projects.update_schedule.assert_called_once_with(
        project.id,
        ScheduleUpdateSchema(
            interval=15,
        ),
    )

    context.scheduler.sync_project.assert_called_once_with(updated)

    callback.answer.assert_awaited_once_with("فاصله زمان‌بندی تغییر کرد.")

    callback.message.edit_text.assert_awaited_once()


@pytest.mark.asyncio
async def test_scheduler_interval_update_survives_scheduler_failure(
    tmp_path: Path,
) -> None:
    updated = build_project(
        tmp_path,
        interval=30,
    )

    callback = build_callback(
        data="sc:is:project-1:s:30",
    )

    context = build_context(
        updated=updated,
        scheduler_error=RuntimeError("scheduler failed"),
    )

    await scheduler_interval_set_callback(
        callback,
        context,
    )

    context.projects.update_schedule.assert_called_once_with(
        "project-1",
        ScheduleUpdateSchema(
            interval=30,
        ),
    )

    context.scheduler.sync_project.assert_called_once_with(updated)

    callback.answer.assert_awaited_once_with("فاصله زمان‌بندی تغییر کرد.")


# =========================================================
# UNIT MENU
# =========================================================


@pytest.mark.asyncio
async def test_scheduler_unit_menu(
    tmp_path: Path,
) -> None:
    project = build_project(
        tmp_path,
        unit=ScheduleUnit.MINUTES,
    )

    callback = build_callback(
        data=(f"sc:u:{project.id}:p"),
    )

    context = build_context(
        project=project,
    )

    await scheduler_unit_callback(
        callback,
        context,
    )

    context.projects.get_project.assert_called_once_with(
        project.id,
    )

    call = callback.message.edit_text.await_args

    assert "تغییر واحد زمان‌بندی" in call.args[0]

    assert "دقیقه" in call.args[0]


# =========================================================
# SET UNIT
# =========================================================


@pytest.mark.asyncio
async def test_scheduler_unit_update(
    tmp_path: Path,
) -> None:
    project = build_project(
        tmp_path,
    )

    updated = build_project(
        tmp_path,
        unit=ScheduleUnit.HOURS,
    )

    callback = build_callback(
        data=(f"sc:us:{project.id}:p:hours"),
    )

    context = build_context(
        updated=updated,
    )

    await scheduler_unit_set_callback(
        callback,
        context,
    )

    context.projects.update_schedule.assert_called_once_with(
        project.id,
        ScheduleUpdateSchema(
            unit=ScheduleUnit.HOURS,
        ),
    )

    context.scheduler.sync_project.assert_called_once_with(updated)

    callback.answer.assert_awaited_once_with("واحد زمان‌بندی تغییر کرد.")

    callback.message.edit_text.assert_awaited_once()


# =========================================================
# PERSISTENCE FAILURE
# =========================================================


@pytest.mark.asyncio
async def test_scheduler_interval_persistence_failure() -> None:
    callback = build_callback(
        data="sc:is:project-1:s:5",
    )

    context = build_context(
        update_error=ProjectPersistenceError("database error"),
    )

    await scheduler_interval_set_callback(
        callback,
        context,
    )

    callback.answer.assert_awaited_once_with(
        "خطا در تغییر فاصله زمان‌بندی.",
        show_alert=True,
    )

    context.scheduler.sync_project.assert_not_called()

    callback.message.edit_text.assert_not_awaited()


@pytest.mark.asyncio
async def test_scheduler_unit_persistence_failure() -> None:
    callback = build_callback(
        data="sc:us:project-1:s:hours",
    )

    context = build_context(
        update_error=ProjectPersistenceError("database error"),
    )

    await scheduler_unit_set_callback(
        callback,
        context,
    )

    callback.answer.assert_awaited_once_with(
        "خطا در تغییر واحد زمان‌بندی.",
        show_alert=True,
    )

    context.scheduler.sync_project.assert_not_called()

    callback.message.edit_text.assert_not_awaited()


# =========================================================
# MALFORMED CALLBACKS
# =========================================================


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "data",
    [
        "sc:p:",
        "sc:p:project-1",
        "sc:p:project-1:x",
    ],
)
async def test_invalid_scheduler_project_callback(
    data: str,
) -> None:
    callback = build_callback(
        data=data,
    )

    context = build_context()

    await scheduler_project_callback(
        callback,
        context,
    )

    callback.answer.assert_awaited_once_with(
        "اطلاعات زمان‌بندی نامعتبر است.",
        show_alert=True,
    )

    callback.message.edit_text.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "data",
    [
        "sc:is:",
        "sc:is:project-1:s",
        "sc:is:project-1:x:5",
        "sc:is:project-1:s:abc",
        "sc:is:project-1:s:0",
    ],
)
async def test_invalid_scheduler_interval_callback(
    data: str,
) -> None:
    callback = build_callback(
        data=data,
    )

    context = build_context()

    await scheduler_interval_set_callback(
        callback,
        context,
    )

    callback.answer.assert_awaited_once()

    context.projects.update_schedule.assert_not_called()

    context.scheduler.sync_project.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "data",
    [
        "sc:us:",
        "sc:us:project-1:s",
        "sc:us:project-1:x:hours",
        "sc:us:project-1:s:invalid",
    ],
)
async def test_invalid_scheduler_unit_callback(
    data: str,
) -> None:
    callback = build_callback(
        data=data,
    )

    context = build_context()

    await scheduler_unit_set_callback(
        callback,
        context,
    )

    callback.answer.assert_awaited_once()

    context.projects.update_schedule.assert_not_called()

    context.scheduler.sync_project.assert_not_called()
