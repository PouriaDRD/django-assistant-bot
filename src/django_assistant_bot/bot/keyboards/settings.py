from __future__ import annotations

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)

# =========================================================
# CALLBACKS
# =========================================================


SETTINGS_CALLBACK = "settings"

BOT_ENABLE_CALLBACK = "settings:bot:enable"

BOT_DISABLE_CALLBACK = "settings:bot:disable"

BACKUP_ENABLE_CALLBACK = "settings:backup:enable"

BACKUP_DISABLE_CALLBACK = "settings:backup:disable"

RETENTION_ENABLE_CALLBACK = "settings:retention:enable"

RETENTION_DISABLE_CALLBACK = "settings:retention:disable"

RETENTION_KEEP_LAST_CALLBACK = "settings:retention:keep-last"

RETENTION_KEEP_LAST_CANCEL_CALLBACK = "settings:retention:keep-last:cancel"


# =========================================================
# SETTINGS KEYBOARD
# =========================================================


def settings_keyboard(
    *,
    bot_enabled: bool,
    backup_enabled: bool,
    retention_enabled: bool,
    retention_keep_last: int,
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

    retention_button = InlineKeyboardButton(
        text=(
            "🧹 غیرفعال کردن Retention"
            if retention_enabled
            else "🧹 فعال کردن Retention"
        ),
        callback_data=(
            RETENTION_DISABLE_CALLBACK
            if retention_enabled
            else RETENTION_ENABLE_CALLBACK
        ),
    )

    retention_keep_last_button = InlineKeyboardButton(
        text=("📦 تعداد بکاپ‌های نگهداری‌شده: " f"{retention_keep_last}"),
        callback_data=(RETENTION_KEEP_LAST_CALLBACK),
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
                retention_button,
            ],
            [
                retention_keep_last_button,
            ],
            [
                InlineKeyboardButton(
                    text="🔙 بازگشت",
                    callback_data="main:menu",
                ),
            ],
        ],
    )


# =========================================================
# RETENTION INPUT KEYBOARD
# =========================================================


def retention_keep_last_keyboard() -> InlineKeyboardMarkup:
    """
    Build keyboard displayed while waiting for a new
    retention keep-last value.
    """

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="❌ لغو",
                    callback_data=(RETENTION_KEEP_LAST_CANCEL_CALLBACK),
                ),
            ],
        ],
    )


# =========================================================
# DISABLED BOT KEYBOARD
# =========================================================


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
    "RETENTION_DISABLE_CALLBACK",
    "RETENTION_ENABLE_CALLBACK",
    "RETENTION_KEEP_LAST_CALLBACK",
    "RETENTION_KEEP_LAST_CANCEL_CALLBACK",
    "SETTINGS_CALLBACK",
    "disabled_bot_keyboard",
    "retention_keep_last_keyboard",
    "settings_keyboard",
]
