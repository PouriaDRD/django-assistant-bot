from __future__ import annotations

from aiogram.types import InlineKeyboardMarkup

from django_assistant_bot.bot.keyboards.settings import (
    BACKUP_DISABLE_CALLBACK,
    BACKUP_ENABLE_CALLBACK,
    BOT_DISABLE_CALLBACK,
    BOT_ENABLE_CALLBACK,
    disabled_bot_keyboard,
    settings_keyboard,
)


def callback_data(
    keyboard: InlineKeyboardMarkup,
) -> list[str]:
    return [
        button.callback_data
        for row in keyboard.inline_keyboard
        for button in row
        if button.callback_data is not None
    ]


def test_enabled_settings_keyboard() -> None:
    keyboard = settings_keyboard(
        bot_enabled=True,
        backup_enabled=True,
    )

    callbacks = callback_data(
        keyboard,
    )

    assert BOT_DISABLE_CALLBACK in callbacks

    assert BACKUP_DISABLE_CALLBACK in callbacks

    assert "main:menu" in callbacks


def test_disabled_backup_settings_keyboard() -> None:
    keyboard = settings_keyboard(
        bot_enabled=True,
        backup_enabled=False,
    )

    callbacks = callback_data(
        keyboard,
    )

    assert BACKUP_ENABLE_CALLBACK in callbacks


def test_disabled_bot_keyboard_only_allows_enable() -> None:
    keyboard = disabled_bot_keyboard()

    assert callback_data(
        keyboard,
    ) == [
        BOT_ENABLE_CALLBACK,
    ]


def test_settings_callbacks_fit_telegram_limit() -> None:
    keyboards: list[InlineKeyboardMarkup] = [
        settings_keyboard(
            bot_enabled=True,
            backup_enabled=True,
        ),
        settings_keyboard(
            bot_enabled=True,
            backup_enabled=False,
        ),
        disabled_bot_keyboard(),
    ]

    for keyboard in keyboards:
        for callback in callback_data(
            keyboard,
        ):
            assert len(callback.encode("utf-8")) <= 64
