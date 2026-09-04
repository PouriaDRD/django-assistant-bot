from __future__ import annotations

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)

SETTINGS_CALLBACK = "settings"

BOT_ENABLE_CALLBACK = "settings:bot:enable"

BOT_DISABLE_CALLBACK = "settings:bot:disable"

BACKUP_ENABLE_CALLBACK = "settings:backup:enable"

BACKUP_DISABLE_CALLBACK = "settings:backup:disable"


def settings_keyboard(
    *,
    bot_enabled: bool,
    backup_enabled: bool,
) -> InlineKeyboardMarkup:
    """
    Build the main settings keyboard.
    """

    bot_button = InlineKeyboardButton(
        text=("🔴 غیرفعال کردن ربات" if bot_enabled else "🟢 فعال کردن ربات"),
        callback_data=(BOT_DISABLE_CALLBACK if bot_enabled else BOT_ENABLE_CALLBACK),
    )

    backup_button = InlineKeyboardButton(
        text=("💾 غیرفعال کردن بکاپ" if backup_enabled else "💾 فعال کردن بکاپ"),
        callback_data=(
            BACKUP_DISABLE_CALLBACK if backup_enabled else BACKUP_ENABLE_CALLBACK
        ),
    )

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                bot_button,
            ],
            [
                backup_button,
            ],
            [
                InlineKeyboardButton(
                    text="🔙 بازگشت",
                    callback_data="main:menu",
                ),
            ],
        ],
    )


def disabled_bot_keyboard() -> InlineKeyboardMarkup:
    """
    Build the only keyboard available while the application
    is globally disabled.
    """

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🟢 فعال کردن ربات",
                    callback_data=BOT_ENABLE_CALLBACK,
                ),
            ],
        ],
    )


__all__ = [
    "BACKUP_DISABLE_CALLBACK",
    "BACKUP_ENABLE_CALLBACK",
    "BOT_DISABLE_CALLBACK",
    "BOT_ENABLE_CALLBACK",
    "SETTINGS_CALLBACK",
    "disabled_bot_keyboard",
    "settings_keyboard",
]
