from __future__ import annotations

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)

from django_assistant_bot.schemas.project import ProjectSchema


def projects_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="➕ افزودن پروژه",
                    callback_data="project:create",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="📋 لیست پروژه‌ها",
                    callback_data="project:list",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🔙 بازگشت",
                    callback_data="main:menu",
                ),
            ],
        ],
    )


def project_list_keyboard(
    projects: list[ProjectSchema],
) -> InlineKeyboardMarkup:
    buttons: list[list[InlineKeyboardButton]] = []

    for project in projects:
        status = "🟢" if project.enabled else "🔴"

        buttons.append(
            [
                InlineKeyboardButton(
                    text=(f"{status} " f"{project.name}"),
                    callback_data=("project:view:" f"{project.id}"),
                ),
            ]
        )

    buttons.append(
        [
            InlineKeyboardButton(
                text="➕ افزودن پروژه",
                callback_data="project:create",
            ),
        ]
    )

    buttons.append(
        [
            InlineKeyboardButton(
                text="🔙 بازگشت",
                callback_data="main:menu",
            ),
        ]
    )

    return InlineKeyboardMarkup(
        inline_keyboard=buttons,
    )


def project_details_keyboard(
    project_id: str,
    enabled: bool,
) -> InlineKeyboardMarkup:
    toggle_button = (
        InlineKeyboardButton(
            text="🔴 غیرفعال کردن",
            callback_data=("project:disable:" f"{project_id}"),
        )
        if enabled
        else InlineKeyboardButton(
            text="🟢 فعال کردن",
            callback_data=("project:enable:" f"{project_id}"),
        )
    )

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="💾 Backup Now",
                    callback_data=("project:backup:" f"{project_id}"),
                ),
            ],
            [
                toggle_button,
            ],
            [
                InlineKeyboardButton(
                    text="🗑 حذف پروژه",
                    callback_data=("project:delete:" f"{project_id}"),
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🔙 پروژه‌ها",
                    callback_data="project:list",
                ),
            ],
        ],
    )


def project_confirmation_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ تأیید و ایجاد",
                    callback_data=("project:create:confirm"),
                ),
            ],
            [
                InlineKeyboardButton(
                    text="❌ لغو",
                    callback_data=("project:create:cancel"),
                ),
            ],
        ],
    )


def schedule_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="15 دقیقه",
                    callback_data=("project:schedule:" "15:minutes"),
                ),
                InlineKeyboardButton(
                    text="30 دقیقه",
                    callback_data=("project:schedule:" "30:minutes"),
                ),
            ],
            [
                InlineKeyboardButton(
                    text="1 ساعت",
                    callback_data=("project:schedule:" "1:hours"),
                ),
                InlineKeyboardButton(
                    text="3 ساعت",
                    callback_data=("project:schedule:" "3:hours"),
                ),
            ],
            [
                InlineKeyboardButton(
                    text="6 ساعت",
                    callback_data=("project:schedule:" "6:hours"),
                ),
                InlineKeyboardButton(
                    text="12 ساعت",
                    callback_data=("project:schedule:" "12:hours"),
                ),
            ],
            [
                InlineKeyboardButton(
                    text="24 ساعت",
                    callback_data=("project:schedule:" "24:hours"),
                ),
            ],
        ],
    )
