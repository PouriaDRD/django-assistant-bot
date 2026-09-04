from __future__ import annotations

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)

# =========================================================
# CALLBACKS
# =========================================================


PROXY_CALLBACK = "proxy"

PROXY_ENABLE_CALLBACK = "proxy:enable"

PROXY_DISABLE_CALLBACK = "proxy:disable"

PROXY_SET_URL_CALLBACK = "proxy:set-url"

PROXY_TEST_CALLBACK = "proxy:test"

PROXY_CLEAR_CALLBACK = "proxy:clear"

PROXY_CANCEL_CALLBACK = "proxy:cancel"


# =========================================================
# MAIN PROXY KEYBOARD
# =========================================================


def proxy_keyboard(
    *,
    proxy_enabled: bool,
    has_proxy_url: bool,
) -> InlineKeyboardMarkup:
    """
    Build proxy management keyboard.
    """

    rows: list[list[InlineKeyboardButton]] = []

    # -----------------------------------------------------
    # STATE
    # -----------------------------------------------------

    if proxy_enabled:
        rows.append(
            [
                InlineKeyboardButton(
                    text="🔴 غیرفعال کردن پروکسی",
                    callback_data=(PROXY_DISABLE_CALLBACK),
                ),
            ]
        )

    elif has_proxy_url:
        rows.append(
            [
                InlineKeyboardButton(
                    text="🟢 فعال کردن پروکسی",
                    callback_data=(PROXY_ENABLE_CALLBACK),
                ),
            ]
        )

    # -----------------------------------------------------
    # CONNECTION TEST
    # -----------------------------------------------------

    if has_proxy_url:
        rows.append(
            [
                InlineKeyboardButton(
                    text="🧪 تست اتصال پروکسی",
                    callback_data=(PROXY_TEST_CALLBACK),
                ),
            ]
        )

    # -----------------------------------------------------
    # URL
    # -----------------------------------------------------

    rows.append(
        [
            InlineKeyboardButton(
                text=(
                    "✏️ تغییر آدرس پروکسی" if has_proxy_url else "➕ تنظیم آدرس پروکسی"
                ),
                callback_data=(PROXY_SET_URL_CALLBACK),
            ),
        ]
    )

    # -----------------------------------------------------
    # CLEAR
    # -----------------------------------------------------

    if has_proxy_url:
        rows.append(
            [
                InlineKeyboardButton(
                    text="🗑 حذف پروکسی",
                    callback_data=(PROXY_CLEAR_CALLBACK),
                ),
            ]
        )

    # -----------------------------------------------------
    # BACK
    # -----------------------------------------------------

    rows.append(
        [
            InlineKeyboardButton(
                text="🔙 بازگشت",
                callback_data="main:menu",
            ),
        ]
    )

    return InlineKeyboardMarkup(
        inline_keyboard=rows,
    )


# =========================================================
# INPUT KEYBOARD
# =========================================================


def proxy_url_input_keyboard() -> InlineKeyboardMarkup:
    """
    Build keyboard shown while waiting for proxy URL.
    """

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="❌ لغو",
                    callback_data=(PROXY_CANCEL_CALLBACK),
                ),
            ],
        ],
    )


# =========================================================
# EXPORTS
# =========================================================


__all__ = [
    "PROXY_CALLBACK",
    "PROXY_CANCEL_CALLBACK",
    "PROXY_CLEAR_CALLBACK",
    "PROXY_DISABLE_CALLBACK",
    "PROXY_ENABLE_CALLBACK",
    "PROXY_SET_URL_CALLBACK",
    "PROXY_TEST_CALLBACK",
    "proxy_keyboard",
    "proxy_url_input_keyboard",
]
