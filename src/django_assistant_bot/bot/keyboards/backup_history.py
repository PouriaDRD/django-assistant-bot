from __future__ import annotations

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)

from django_assistant_bot.database.models.enums import (
    BackupStatus,
)
from django_assistant_bot.schemas.backup import (
    BackupHistorySchema,
)
from django_assistant_bot.schemas.project import (
    ProjectSchema,
)

# Telegram callback_data has a strict 64-byte limit.
# Keep callback prefixes intentionally short.
HISTORY_PROJECT_PREFIX = "bh:p:"
HISTORY_DETAIL_PREFIX = "bh:d:"


def build_backup_history_projects_keyboard(
    projects: list[ProjectSchema],
) -> InlineKeyboardMarkup:
    """
    Build project selector keyboard for backup history.
    """

    rows: list[list[InlineKeyboardButton]] = []

    for project in projects:
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"📦 {project.name}",
                    callback_data=(f"{HISTORY_PROJECT_PREFIX}" f"{project.id}:0"),
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


def build_backup_history_list_keyboard(
    *,
    project_id: str,
    histories: list[BackupHistorySchema],
    page: int,
    has_next: bool,
) -> InlineKeyboardMarkup:
    """
    Build paginated backup history keyboard.
    """

    rows: list[list[InlineKeyboardButton]] = []

    for history in histories:
        status_icon = "✅" if history.status is BackupStatus.SUCCESS else "❌"

        rows.append(
            [
                InlineKeyboardButton(
                    text=(f"{status_icon} " "مشاهده جزئیات"),
                    callback_data=(
                        f"{HISTORY_DETAIL_PREFIX}" f"{history.id}:" f"{page}"
                    ),
                )
            ]
        )

    navigation: list[InlineKeyboardButton] = []

    if page > 0:
        navigation.append(
            InlineKeyboardButton(
                text="⬅️ قبلی",
                callback_data=(
                    f"{HISTORY_PROJECT_PREFIX}" f"{project_id}:" f"{page - 1}"
                ),
            )
        )

    if has_next:
        navigation.append(
            InlineKeyboardButton(
                text="بعدی ➡️",
                callback_data=(
                    f"{HISTORY_PROJECT_PREFIX}" f"{project_id}:" f"{page + 1}"
                ),
            )
        )

    if navigation:
        rows.append(navigation)

    rows.append(
        [
            InlineKeyboardButton(
                text="📦 انتخاب پروژه",
                callback_data="backup:history",
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


def build_backup_history_detail_keyboard(
    *,
    project_id: str,
    page: int,
) -> InlineKeyboardMarkup:
    """
    Build backup history detail navigation keyboard.
    """

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔙 بازگشت به تاریخچه",
                    callback_data=(
                        f"{HISTORY_PROJECT_PREFIX}" f"{project_id}:" f"{page}"
                    ),
                )
            ],
            [
                InlineKeyboardButton(
                    text="💾 بکاپ",
                    callback_data="backup",
                )
            ],
        ]
    )


__all__ = [
    "HISTORY_DETAIL_PREFIX",
    "HISTORY_PROJECT_PREFIX",
    "build_backup_history_detail_keyboard",
    "build_backup_history_list_keyboard",
    "build_backup_history_projects_keyboard",
]
