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

from django_assistant_bot.bot.handlers.settings import (
    disable_backups_callback,
    disable_bot_callback,
    enable_backups_callback,
    enable_bot_callback,
    settings_menu_callback,
)
from django_assistant_bot.bot.keyboards.settings import (
    BACKUP_DISABLE_CALLBACK,
    BACKUP_ENABLE_CALLBACK,
    BOT_DISABLE_CALLBACK,
    BOT_ENABLE_CALLBACK,
)
from django_assistant_bot.schemas.app_settings import (
    AppSettingsSchema,
)
from django_assistant_bot.services.settings import (
    SettingsPersistenceError,
)

# =========================================================
# BUILDERS
# =========================================================


def build_settings(
    *,
    bot_enabled: bool = True,
    backup_enabled: bool = True,
) -> AppSettingsSchema:
    return AppSettingsSchema(
        bot_enabled=bot_enabled,
        backup_enabled=backup_enabled,
    )


def build_callback(
    *,
    data: str,
) -> Mock:
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
    settings: Mock | None = None,
    scheduler: Mock | None = None,
    projects: Mock | None = None,
) -> SimpleNamespace:
    settings_service = settings if settings is not None else Mock()

    scheduler_service = scheduler if scheduler is not None else Mock()

    project_service = projects if projects is not None else Mock()

    return SimpleNamespace(
        settings=settings_service,
        scheduler=scheduler_service,
        projects=project_service,
    )


# =========================================================
# SETTINGS MENU
# =========================================================


@pytest.mark.asyncio
async def test_settings_menu_displays_current_settings() -> None:
    current = build_settings(
        bot_enabled=True,
        backup_enabled=False,
    )

    settings = Mock()

    settings.get_settings.return_value = current

    callback = build_callback(
        data="settings",
    )

    context = build_context(
        settings=settings,
    )

    await settings_menu_callback(
        callback,
        context,
    )

    callback.answer.assert_awaited_once_with()

    settings.get_settings.assert_called_once_with()

    callback.message.edit_text.assert_awaited_once()

    call = callback.message.edit_text.await_args

    text = call.args[0]

    keyboard = call.kwargs["reply_markup"]

    assert "⚙️" in text
    assert "تنظیمات" in text

    assert "🟢 فعال" in text

    callbacks = [
        button.callback_data
        for row in keyboard.inline_keyboard
        for button in row
        if button.callback_data is not None
    ]

    assert BOT_DISABLE_CALLBACK in callbacks

    assert BACKUP_ENABLE_CALLBACK in callbacks

    assert "main:menu" in callbacks


@pytest.mark.asyncio
async def test_settings_menu_handles_persistence_error() -> None:
    settings = Mock()

    settings.get_settings.side_effect = SettingsPersistenceError("database unavailable")

    callback = build_callback(
        data="settings",
    )

    context = build_context(
        settings=settings,
    )

    await settings_menu_callback(
        callback,
        context,
    )

    assert callback.answer.await_count == 2

    callback.answer.assert_any_await()

    callback.answer.assert_any_await(
        "خطا در دریافت تنظیمات.",
        show_alert=True,
    )

    callback.message.edit_text.assert_not_awaited()


# =========================================================
# BOT DISABLE
# =========================================================


@pytest.mark.asyncio
async def test_disable_bot_persists_state_and_pauses_scheduler() -> None:
    settings = Mock()

    settings.disable_bot.return_value = build_settings(
        bot_enabled=False,
    )

    scheduler = Mock()

    callback = build_callback(
        data=BOT_DISABLE_CALLBACK,
    )

    context = build_context(
        settings=settings,
        scheduler=scheduler,
    )

    await disable_bot_callback(
        callback,
        context,
    )

    settings.disable_bot.assert_called_once_with()

    scheduler.pause.assert_called_once_with()

    callback.answer.assert_awaited_once_with("ربات غیرفعال شد.")

    callback.message.edit_text.assert_awaited_once()

    call = callback.message.edit_text.await_args

    text = call.args[0]

    keyboard = call.kwargs["reply_markup"]

    assert "ربات غیرفعال شد" in text

    callbacks = [
        button.callback_data
        for row in keyboard.inline_keyboard
        for button in row
        if button.callback_data is not None
    ]

    assert callbacks == [
        BOT_ENABLE_CALLBACK,
    ]


@pytest.mark.asyncio
async def test_disable_bot_survives_scheduler_pause_failure() -> None:
    settings = Mock()

    settings.disable_bot.return_value = build_settings(
        bot_enabled=False,
    )

    scheduler = Mock()

    scheduler.pause.side_effect = RuntimeError("scheduler unavailable")

    callback = build_callback(
        data=BOT_DISABLE_CALLBACK,
    )

    context = build_context(
        settings=settings,
        scheduler=scheduler,
    )

    await disable_bot_callback(
        callback,
        context,
    )

    settings.disable_bot.assert_called_once_with()

    scheduler.pause.assert_called_once_with()

    callback.answer.assert_awaited_once_with("ربات غیرفعال شد.")

    callback.message.edit_text.assert_awaited_once()


@pytest.mark.asyncio
async def test_disable_bot_handles_persistence_error() -> None:
    settings = Mock()

    settings.disable_bot.side_effect = SettingsPersistenceError("database unavailable")

    scheduler = Mock()

    callback = build_callback(
        data=BOT_DISABLE_CALLBACK,
    )

    context = build_context(
        settings=settings,
        scheduler=scheduler,
    )

    await disable_bot_callback(
        callback,
        context,
    )

    callback.answer.assert_awaited_once_with(
        "خطا در غیرفعال کردن ربات.",
        show_alert=True,
    )

    scheduler.pause.assert_not_called()

    callback.message.edit_text.assert_not_awaited()


# =========================================================
# BOT ENABLE
# =========================================================


@pytest.mark.asyncio
async def test_enable_bot_resumes_scheduler_and_returns_to_main_menu() -> None:
    current = build_settings(
        bot_enabled=True,
        backup_enabled=True,
    )

    settings = Mock()

    settings.enable_bot.return_value = current

    settings.get_settings.return_value = current

    scheduler = Mock()

    projects = Mock()

    projects.list_projects.return_value = []

    callback = build_callback(
        data=BOT_ENABLE_CALLBACK,
    )

    context = build_context(
        settings=settings,
        scheduler=scheduler,
        projects=projects,
    )

    await enable_bot_callback(
        callback,
        context,
    )

    settings.enable_bot.assert_called_once_with()

    scheduler.resume.assert_called_once_with()

    callback.answer.assert_awaited_once_with("ربات فعال شد.")

    projects.list_projects.assert_called_once_with()

    settings.get_settings.assert_called_once_with()

    callback.message.edit_text.assert_awaited_once()

    call = callback.message.edit_text.await_args

    text = call.args[0]

    keyboard = call.kwargs["reply_markup"]

    assert "Django Assistant Bot" in text

    assert "وضعیت ربات: 🟢 فعال" in text

    callbacks = [
        button.callback_data
        for row in keyboard.inline_keyboard
        for button in row
        if button.callback_data is not None
    ]

    assert "projects" in callbacks
    assert "backup" in callbacks
    assert "scheduler" in callbacks
    assert "settings" in callbacks


@pytest.mark.asyncio
async def test_enable_bot_survives_scheduler_resume_failure() -> None:
    current = build_settings(
        bot_enabled=True,
        backup_enabled=True,
    )

    settings = Mock()

    settings.enable_bot.return_value = current

    settings.get_settings.return_value = current

    scheduler = Mock()

    scheduler.resume.side_effect = RuntimeError("scheduler unavailable")

    projects = Mock()

    projects.list_projects.return_value = []

    callback = build_callback(
        data=BOT_ENABLE_CALLBACK,
    )

    context = build_context(
        settings=settings,
        scheduler=scheduler,
        projects=projects,
    )

    await enable_bot_callback(
        callback,
        context,
    )

    settings.enable_bot.assert_called_once_with()

    scheduler.resume.assert_called_once_with()

    callback.answer.assert_awaited_once_with(
        ("ربات فعال شد، اما راه‌اندازی " "زمان‌بندی با خطا مواجه شد."),
        show_alert=True,
    )

    callback.message.edit_text.assert_awaited_once()


@pytest.mark.asyncio
async def test_enable_bot_handles_persistence_error() -> None:
    settings = Mock()

    settings.enable_bot.side_effect = SettingsPersistenceError("database unavailable")

    scheduler = Mock()

    callback = build_callback(
        data=BOT_ENABLE_CALLBACK,
    )

    context = build_context(
        settings=settings,
        scheduler=scheduler,
    )

    await enable_bot_callback(
        callback,
        context,
    )

    callback.answer.assert_awaited_once_with(
        "خطا در فعال کردن ربات.",
        show_alert=True,
    )

    scheduler.resume.assert_not_called()

    callback.message.edit_text.assert_not_awaited()


# =========================================================
# BACKUP ENABLE
# =========================================================


@pytest.mark.asyncio
async def test_enable_backups_updates_settings_screen() -> None:
    updated = build_settings(
        bot_enabled=True,
        backup_enabled=True,
    )

    settings = Mock()

    settings.enable_backups.return_value = updated

    callback = build_callback(
        data=BACKUP_ENABLE_CALLBACK,
    )

    context = build_context(
        settings=settings,
    )

    await enable_backups_callback(
        callback,
        context,
    )

    settings.enable_backups.assert_called_once_with()

    callback.answer.assert_awaited_once_with("بکاپ‌ها فعال شدند.")

    callback.message.edit_text.assert_awaited_once()

    call = callback.message.edit_text.await_args

    keyboard = call.kwargs["reply_markup"]

    callbacks = [
        button.callback_data
        for row in keyboard.inline_keyboard
        for button in row
        if button.callback_data is not None
    ]

    assert BACKUP_DISABLE_CALLBACK in callbacks


@pytest.mark.asyncio
async def test_enable_backups_handles_persistence_error() -> None:
    settings = Mock()

    settings.enable_backups.side_effect = SettingsPersistenceError(
        "database unavailable"
    )

    callback = build_callback(
        data=BACKUP_ENABLE_CALLBACK,
    )

    context = build_context(
        settings=settings,
    )

    await enable_backups_callback(
        callback,
        context,
    )

    callback.answer.assert_awaited_once_with(
        "خطا در فعال کردن بکاپ‌ها.",
        show_alert=True,
    )

    callback.message.edit_text.assert_not_awaited()


# =========================================================
# BACKUP DISABLE
# =========================================================


@pytest.mark.asyncio
async def test_disable_backups_updates_settings_screen() -> None:
    updated = build_settings(
        bot_enabled=True,
        backup_enabled=False,
    )

    settings = Mock()

    settings.disable_backups.return_value = updated

    callback = build_callback(
        data=BACKUP_DISABLE_CALLBACK,
    )

    context = build_context(
        settings=settings,
    )

    await disable_backups_callback(
        callback,
        context,
    )

    settings.disable_backups.assert_called_once_with()

    callback.answer.assert_awaited_once_with("بکاپ‌ها غیرفعال شدند.")

    callback.message.edit_text.assert_awaited_once()

    call = callback.message.edit_text.await_args

    keyboard = call.kwargs["reply_markup"]

    callbacks = [
        button.callback_data
        for row in keyboard.inline_keyboard
        for button in row
        if button.callback_data is not None
    ]

    assert BACKUP_ENABLE_CALLBACK in callbacks


@pytest.mark.asyncio
async def test_disable_backups_handles_persistence_error() -> None:
    settings = Mock()

    settings.disable_backups.side_effect = SettingsPersistenceError(
        "database unavailable"
    )

    callback = build_callback(
        data=BACKUP_DISABLE_CALLBACK,
    )

    context = build_context(
        settings=settings,
    )

    await disable_backups_callback(
        callback,
        context,
    )

    callback.answer.assert_awaited_once_with(
        "خطا در غیرفعال کردن بکاپ‌ها.",
        show_alert=True,
    )

    callback.message.edit_text.assert_not_awaited()
