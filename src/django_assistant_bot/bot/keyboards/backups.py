from __future__ import annotations

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)

from django_assistant_bot.schemas.project import (
    ProjectSchema,
)


def backup_projects_keyboard(
    projects: list[ProjectSchema],
) -> InlineKeyboardMarkup:
    """
    Build project selection keyboard for manual backups.
    """

    buttons: list[list[InlineKeyboardButton]] = []

    for project in projects:
        status = "🟢" if project.enabled else "🔴"

        label = f"{status} {project.name}"

        buttons.append(
            [
                InlineKeyboardButton(
                    text=label,
                    callback_data=("project:backup:" f"{project.id}"),
                )
            ]
        )

    buttons.append(
        [
            InlineKeyboardButton(
                text="🔙 بازگشت",
                callback_data="main:menu",
            )
        ]
    )

    return InlineKeyboardMarkup(
        inline_keyboard=buttons,
    )
