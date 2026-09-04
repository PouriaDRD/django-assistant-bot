from __future__ import annotations

from aiogram.types import (
    InlineKeyboardMarkup,
)

from django_assistant_bot.bot.keyboards.system_status import (
    SYSTEM_STATUS_REFRESH_CALLBACK,
    system_status_keyboard,
)


def _callback_data(
    keyboard: InlineKeyboardMarkup,
) -> list[str]:
    return [
        button.callback_data
        for row in keyboard.inline_keyboard
        for button in row
        if button.callback_data is not None
    ]


def test_system_status_keyboard_contains_refresh() -> None:
    keyboard = system_status_keyboard()

    callbacks = _callback_data(keyboard)

    assert SYSTEM_STATUS_REFRESH_CALLBACK in callbacks


def test_system_status_keyboard_contains_back() -> None:
    keyboard = system_status_keyboard()

    callbacks = _callback_data(keyboard)

    assert "main:menu" in callbacks


def test_system_status_callbacks_fit_telegram_limit() -> None:
    keyboard = system_status_keyboard()

    callbacks = _callback_data(keyboard)

    for callback_data in callbacks:
        assert len(callback_data.encode("utf-8")) <= 64
