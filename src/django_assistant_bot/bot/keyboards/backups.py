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

    rows: list[list[InlineKeyboardButton]] = []

    for project in projects:
        status_icon = "🟢" if project.enabled else "🔴"

        rows.append(
            [
                InlineKeyboardButton(
                    text=(f"{status_icon} " f"{project.name}"),
                    callback_data=("project:backup:" f"{project.id}"),
                )
            ]
        )

    rows.append(
        [
            InlineKeyboardButton(
                text="🔙 بازگشت",
                callback_data="backup",
            )
        ]
    )

    return InlineKeyboardMarkup(
        inline_keyboard=rows,
    )


__all__ = [
    "backup_projects_keyboard",
]
