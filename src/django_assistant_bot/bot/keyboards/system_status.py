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

SYSTEM_STATUS_OVERVIEW_CALLBACK = "system_status:overview"

SYSTEM_STATUS_SERVICES_CALLBACK = "system_status:services"

SYSTEM_STATUS_RESOURCES_CALLBACK = "system_status:resources"

SYSTEM_STATUS_BACKUP_CALLBACK = "system_status:backup"

SYSTEM_STATUS_PROJECTS_CALLBACK = "system_status:projects"

SYSTEM_STATUS_SYSTEM_CALLBACK = "system_status:system"

MAIN_MENU_CALLBACK = "main:menu"


# =========================================================
# MAIN DASHBOARD KEYBOARD
# =========================================================


def system_status_keyboard() -> InlineKeyboardMarkup:
    """
    Build main system-status navigation keyboard.
    """

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="⚙️ سرویس‌ها",
                    callback_data=(SYSTEM_STATUS_SERVICES_CALLBACK),
                ),
                InlineKeyboardButton(
                    text="📊 منابع",
                    callback_data=(SYSTEM_STATUS_RESOURCES_CALLBACK),
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🗃 آخرین بکاپ",
                    callback_data=(SYSTEM_STATUS_BACKUP_CALLBACK),
                ),
                InlineKeyboardButton(
                    text="📦 پروژه‌ها",
                    callback_data=(SYSTEM_STATUS_PROJECTS_CALLBACK),
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🖥 سیستم",
                    callback_data=(SYSTEM_STATUS_SYSTEM_CALLBACK),
                ),
            ],
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


# =========================================================
# DETAIL KEYBOARD
# =========================================================


def system_status_detail_keyboard(
    *,
    refresh_callback: str,
) -> InlineKeyboardMarkup:
    """
    Build keyboard used by system-status detail pages.
    """

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔄 بروزرسانی",
                    callback_data=(refresh_callback),
                ),
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ وضعیت سیستم",
                    callback_data=(SYSTEM_STATUS_OVERVIEW_CALLBACK),
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🏠 منوی اصلی",
                    callback_data=(MAIN_MENU_CALLBACK),
                ),
            ],
        ],
    )


__all__ = [
    "MAIN_MENU_CALLBACK",
    "SYSTEM_STATUS_BACKUP_CALLBACK",
    "SYSTEM_STATUS_CALLBACK",
    "SYSTEM_STATUS_OVERVIEW_CALLBACK",
    "SYSTEM_STATUS_PROJECTS_CALLBACK",
    "SYSTEM_STATUS_REFRESH_CALLBACK",
    "SYSTEM_STATUS_RESOURCES_CALLBACK",
    "SYSTEM_STATUS_SERVICES_CALLBACK",
    "SYSTEM_STATUS_SYSTEM_CALLBACK",
    "system_status_detail_keyboard",
    "system_status_keyboard",
]
