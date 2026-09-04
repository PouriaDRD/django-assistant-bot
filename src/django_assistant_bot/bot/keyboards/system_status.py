from __future__ import annotations

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)

# =========================================================
# CALLBACKS
# =========================================================


SYSTEM_STATUS_CALLBACK = "system_status"

SYSTEM_STATUS_REFRESH_CALLBACK = "system_status:refresh"

MAIN_MENU_CALLBACK = "main:menu"


# =========================================================
# KEYBOARD
# =========================================================


def system_status_keyboard() -> InlineKeyboardMarkup:
    """
    Build system status actions keyboard.
    """

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔄 بروزرسانی",
                    callback_data=(SYSTEM_STATUS_REFRESH_CALLBACK),
                ),
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ بازگشت",
                    callback_data=(MAIN_MENU_CALLBACK),
                ),
            ],
        ],
    )


__all__ = [
    "MAIN_MENU_CALLBACK",
    "SYSTEM_STATUS_CALLBACK",
    "SYSTEM_STATUS_REFRESH_CALLBACK",
    "system_status_keyboard",
]
