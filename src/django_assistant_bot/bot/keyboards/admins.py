from __future__ import annotations

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)

from django_assistant_bot.schemas.admin import (
    AdminSchema,
)

ADMINS_CALLBACK = "admins"

ADMIN_ADD_CALLBACK = "admin:add"

ADMIN_DELETE_PREFIX = "admin:delete:"

ADMIN_CANCEL_CALLBACK = "admin:cancel"


def admins_menu_keyboard(
    admins: list[AdminSchema],
) -> InlineKeyboardMarkup:
    """
    Build administrator management keyboard.
    """

    rows: list[list[InlineKeyboardButton]] = [
        [
            InlineKeyboardButton(
                text="➕ افزودن ادمین",
                callback_data=(ADMIN_ADD_CALLBACK),
            ),
        ],
    ]

    if len(admins) > 1:
        rows.append(
            [
                InlineKeyboardButton(
                    text="➖ حذف ادمین",
                    callback_data=("admin:delete:list"),
                ),
            ]
        )

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


def admin_delete_keyboard(
    admins: list[AdminSchema],
) -> InlineKeyboardMarkup:
    """
    Build administrator deletion keyboard.
    """

    rows: list[list[InlineKeyboardButton]] = []

    for admin in admins:
        rows.append(
            [
                InlineKeyboardButton(
                    text=("🗑 " f"{admin.telegram_user_id}"),
                    callback_data=(
                        f"{ADMIN_DELETE_PREFIX}" f"{admin.telegram_user_id}"
                    ),
                ),
            ]
        )

    rows.append(
        [
            InlineKeyboardButton(
                text="🔙 بازگشت",
                callback_data=ADMINS_CALLBACK,
            ),
        ]
    )

    return InlineKeyboardMarkup(
        inline_keyboard=rows,
    )


def admin_creation_keyboard() -> InlineKeyboardMarkup:
    """
    Build admin creation cancellation keyboard.
    """

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="❌ لغو",
                    callback_data=(ADMIN_CANCEL_CALLBACK),
                ),
            ],
        ],
    )


__all__ = [
    "ADMIN_ADD_CALLBACK",
    "ADMIN_CANCEL_CALLBACK",
    "ADMIN_DELETE_PREFIX",
    "ADMINS_CALLBACK",
    "admin_creation_keyboard",
    "admin_delete_keyboard",
    "admins_menu_keyboard",
]
