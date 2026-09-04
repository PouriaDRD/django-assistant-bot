from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import (
    AsyncMock,
    Mock,
)

import pytest
from aiogram.types import (
    CallbackQuery,
    Message,
)

from django_assistant_bot.bot.handlers.system_status import (
    system_status_callback,
    system_status_refresh_callback,
)
from django_assistant_bot.bot.keyboards.system_status import (
    SYSTEM_STATUS_CALLBACK,
    SYSTEM_STATUS_REFRESH_CALLBACK,
)
from django_assistant_bot.schemas.system_status import (
    SchedulerRuntimeStatus,
    SystemStatusSchema,
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

# =========================================================
# BUILDERS
# =========================================================


def build_status() -> SystemStatusSchema:
    """
    Build complete system status snapshot for handler tests.
    """

    gib = 1024**3

    return SystemStatusSchema(
        # -------------------------------------------------
        # APPLICATION
        # -------------------------------------------------
        bot_enabled=True,
        backup_enabled=True,
        proxy_enabled=False,
        retention_enabled=True,
        database_healthy=True,
        scheduler_status=(SchedulerRuntimeStatus.RUNNING),
        uptime_seconds=(2 * 60 * 60 + 18 * 60),
        # -------------------------------------------------
        # PROJECTS
        # -------------------------------------------------
        project_count=3,
        enabled_project_count=2,
        scheduled_project_count=1,
        admin_count=2,
        # -------------------------------------------------
        # RUNTIME
        # -------------------------------------------------
        python_version="3.13.14",
        operating_system="Windows",
        operating_system_version=("11 (10.0.26100)"),
        architecture="AMD64",
        # -------------------------------------------------
        # CPU
        # -------------------------------------------------
        cpu_usage_percent=25.4,
        cpu_physical_cores=8,
        cpu_logical_cores=16,
        # -------------------------------------------------
        # MEMORY
        # -------------------------------------------------
        memory_total_bytes=16 * gib,
        memory_used_bytes=6 * gib,
        memory_available_bytes=10 * gib,
        memory_usage_percent=37.5,
        # -------------------------------------------------
        # DISK
        # -------------------------------------------------
        disk_total_bytes=512 * gib,
        disk_used_bytes=256 * gib,
        disk_free_bytes=256 * gib,
        disk_usage_percent=50.0,
    )


def build_callback(
    *,
    data: str,
) -> Mock:
    """
    Build callback query mock.
    """

    message = Mock(
        spec=Message,
    )

    message.edit_text = AsyncMock()

    callback = Mock(
        spec=CallbackQuery,
    )

    callback.data = data

    callback.message = message

    callback.answer = AsyncMock()

    return callback


def build_context(
    *,
    system_status: Mock,
) -> SimpleNamespace:
    """
    Build minimal application context.
    """

    return SimpleNamespace(
        system_status=system_status,
    )


# =========================================================
# DISPLAY
# =========================================================


@pytest.mark.asyncio
async def test_system_status_callback_displays_status() -> None:
    system_status = Mock()

    system_status.get_status.return_value = build_status()

    callback = build_callback(
        data=SYSTEM_STATUS_CALLBACK,
    )

    context = build_context(
        system_status=system_status,
    )

    await system_status_callback(
        callback,
        context,
    )

    system_status.get_status.assert_called_once_with()

    callback.answer.assert_awaited_once_with()

    callback.message.edit_text.assert_awaited_once()

    call = callback.message.edit_text.await_args

    text = call.args[0]

    keyboard = call.kwargs["reply_markup"]

    # -----------------------------------------------------
    # GENERAL
    # -----------------------------------------------------

    assert "وضعیت سیستم" in text

    assert "سیستم در وضعیت عادی قرار دارد" in text

    # -----------------------------------------------------
    # SERVICES
    # -----------------------------------------------------

    assert "سرویس‌ها" in text

    assert "ربات" in text

    assert "سیستم بکاپ" in text

    assert "زمان‌بندی" in text

    assert "دیتابیس" in text

    assert "در دسترس نیست" not in text

    assert "پروکسی" in text

    assert "نگهداری بکاپ" in text

    # -----------------------------------------------------
    # UPTIME
    # -----------------------------------------------------

    assert "زمان اجرا" in text

    assert "2 ساعت" in text

    assert "18 دقیقه" in text

    # -----------------------------------------------------
    # RESOURCES
    # -----------------------------------------------------

    assert "منابع سیستم" in text

    assert "حافظه" in text

    assert "پردازنده" in text

    assert "فضای ذخیره‌سازی" in text

    assert "37.5%" in text

    assert "25.4%" in text

    assert "50.0%" in text

    # -----------------------------------------------------
    # PROJECTS
    # -----------------------------------------------------

    assert "پروژه‌ها" in text

    assert "ادمین‌ها" in text

    # -----------------------------------------------------
    # SYSTEM INFORMATION
    # -----------------------------------------------------

    assert "اطلاعات سیستم" in text

    assert "سیستم‌عامل" in text

    assert "Windows" in text

    assert "11" in text

    assert "10.0.26100" in text

    assert "AMD64" in text

    assert "3.13.14" in text

    # -----------------------------------------------------
    # KEYBOARD
    # -----------------------------------------------------

    callbacks = [
        button.callback_data
        for row in keyboard.inline_keyboard
        for button in row
        if button.callback_data is not None
    ]

    assert SYSTEM_STATUS_REFRESH_CALLBACK in callbacks

    assert "main:menu" in callbacks


# =========================================================
# REFRESH
# =========================================================


@pytest.mark.asyncio
async def test_system_status_refresh_callback_reloads_status() -> None:
    system_status = Mock()

    system_status.get_status.return_value = build_status()

    callback = build_callback(
        data=SYSTEM_STATUS_REFRESH_CALLBACK,
    )

    context = build_context(
        system_status=system_status,
    )

    await system_status_refresh_callback(
        callback,
        context,
    )

    system_status.get_status.assert_called_once_with()

    callback.answer.assert_awaited_once_with()

    callback.message.edit_text.assert_awaited_once()


# =========================================================
# ERROR HANDLING
# =========================================================


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "error",
    [
        SettingsPersistenceError("settings unavailable"),
        ProjectPersistenceError("projects unavailable"),
        AdminPersistenceError("admins unavailable"),
    ],
)
async def test_system_status_handles_persistence_errors(
    error: Exception,
) -> None:
    system_status = Mock()

    system_status.get_status.side_effect = error

    callback = build_callback(
        data=SYSTEM_STATUS_CALLBACK,
    )

    context = build_context(
        system_status=system_status,
    )

    await system_status_callback(
        callback,
        context,
    )

    callback.answer.assert_awaited_once_with(
        "خطا در دریافت وضعیت سیستم.",
        show_alert=True,
    )

    callback.message.edit_text.assert_not_awaited()


# =========================================================
# NON-MESSAGE CALLBACK
# =========================================================


@pytest.mark.asyncio
async def test_system_status_ignores_non_message_callback() -> None:
    system_status = Mock()

    system_status.get_status.return_value = build_status()

    callback = Mock(
        spec=CallbackQuery,
    )

    callback.data = SYSTEM_STATUS_CALLBACK

    callback.message = None

    callback.answer = AsyncMock()

    context = build_context(
        system_status=system_status,
    )

    await system_status_callback(
        callback,
        context,
    )

    system_status.get_status.assert_called_once_with()

    callback.answer.assert_awaited_once_with()
