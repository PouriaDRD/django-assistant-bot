from __future__ import annotations

from aiogram.types import (
    InlineKeyboardMarkup,
)

from django_assistant_bot.bot.keyboards.settings import (
    BACKUP_DISABLE_CALLBACK,
    BACKUP_ENABLE_CALLBACK,
    BOT_DISABLE_CALLBACK,
    BOT_ENABLE_CALLBACK,
    RETENTION_DISABLE_CALLBACK,
    RETENTION_ENABLE_CALLBACK,
    RETENTION_KEEP_LAST_CALLBACK,
    RETENTION_KEEP_LAST_CANCEL_CALLBACK,
    disabled_bot_keyboard,
    retention_keep_last_keyboard,
    settings_keyboard,
)

# =========================================================
# HELPERS
# =========================================================


def callback_data(
    keyboard: InlineKeyboardMarkup,
) -> list[str]:
    """
    Return all callback_data values from a keyboard.
    """

    return [
        button.callback_data
        for row in keyboard.inline_keyboard
        for button in row
        if button.callback_data is not None
    ]


def button_texts(
    keyboard: InlineKeyboardMarkup,
) -> list[str]:
    """
    Return all button texts from a keyboard.
    """

    return [button.text for row in keyboard.inline_keyboard for button in row]


# =========================================================
# ENABLED SETTINGS
# =========================================================


def test_enabled_settings_keyboard() -> None:
    keyboard = settings_keyboard(
        bot_enabled=True,
        backup_enabled=True,
        retention_enabled=True,
        retention_keep_last=10,
    )

    callbacks = callback_data(
        keyboard,
    )

    assert BOT_DISABLE_CALLBACK in callbacks

    assert BACKUP_DISABLE_CALLBACK in callbacks

    assert RETENTION_DISABLE_CALLBACK in callbacks

    assert RETENTION_KEEP_LAST_CALLBACK in callbacks

    assert "main:menu" in callbacks


# =========================================================
# DISABLED BACKUP
# =========================================================


def test_disabled_backup_settings_keyboard() -> None:
    keyboard = settings_keyboard(
        bot_enabled=True,
        backup_enabled=False,
        retention_enabled=True,
        retention_keep_last=10,
    )

    callbacks = callback_data(
        keyboard,
    )

    assert BACKUP_ENABLE_CALLBACK in callbacks

    assert RETENTION_DISABLE_CALLBACK in callbacks


# =========================================================
# DISABLED RETENTION
# =========================================================


def test_disabled_retention_settings_keyboard() -> None:
    keyboard = settings_keyboard(
        bot_enabled=True,
        backup_enabled=True,
        retention_enabled=False,
        retention_keep_last=10,
    )

    callbacks = callback_data(
        keyboard,
    )

    assert RETENTION_ENABLE_CALLBACK in callbacks

    assert RETENTION_DISABLE_CALLBACK not in callbacks

    assert RETENTION_KEEP_LAST_CALLBACK in callbacks


# =========================================================
# RETENTION KEEP-LAST VALUE
# =========================================================


def test_retention_keep_last_value_is_displayed() -> None:
    keyboard = settings_keyboard(
        bot_enabled=True,
        backup_enabled=True,
        retention_enabled=True,
        retention_keep_last=25,
    )

    texts = button_texts(
        keyboard,
    )

    assert any("25" in text for text in texts)


# =========================================================
# RETENTION INPUT KEYBOARD
# =========================================================


def test_retention_keep_last_keyboard_only_allows_cancel() -> None:
    keyboard = retention_keep_last_keyboard()

    assert callback_data(
        keyboard,
    ) == [
        RETENTION_KEEP_LAST_CANCEL_CALLBACK,
    ]


# =========================================================
# DISABLED BOT
# =========================================================


def test_disabled_bot_keyboard_only_allows_enable() -> None:
    keyboard = disabled_bot_keyboard()

    assert callback_data(
        keyboard,
    ) == [
        BOT_ENABLE_CALLBACK,
    ]


# =========================================================
# CALLBACK LENGTH
# =========================================================


def test_settings_callbacks_fit_telegram_limit() -> None:
    keyboards: list[InlineKeyboardMarkup] = [
        settings_keyboard(
            bot_enabled=True,
            backup_enabled=True,
            retention_enabled=True,
            retention_keep_last=10,
        ),
        settings_keyboard(
            bot_enabled=True,
            backup_enabled=False,
            retention_enabled=True,
            retention_keep_last=10,
        ),
        settings_keyboard(
            bot_enabled=True,
            backup_enabled=True,
            retention_enabled=False,
            retention_keep_last=25,
        ),
        retention_keep_last_keyboard(),
        disabled_bot_keyboard(),
    ]

    for keyboard in keyboards:
        for callback in callback_data(
            keyboard,
        ):
            assert len(callback.encode("utf-8")) <= 64
