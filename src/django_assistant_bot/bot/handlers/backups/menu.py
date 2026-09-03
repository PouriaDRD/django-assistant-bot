from __future__ import annotations

from aiogram import (
    F,
    Router,
)
from aiogram.types import (
    CallbackQuery,
    Message,
)

from django_assistant_bot.bot.context import (
    ApplicationContext,
)
from django_assistant_bot.bot.keyboards.backups import (
    backup_projects_keyboard,
)

router = Router(
    name="backups.menu",
)


@router.callback_query(
    F.data == "backup",
)
async def backup_menu_callback(
    callback: CallbackQuery,
    context: ApplicationContext,
) -> None:
    """
    Display projects available for manual backup.
    """

    projects = context.projects.list_projects()

    await callback.answer()

    if not isinstance(
        callback.message,
        Message,
    ):
        return

    if not projects:
        await callback.message.edit_text(
            "💾 <b>بکاپ</b>\n"
            "\n"
            "هنوز هیچ پروژه‌ای ثبت نشده است.\n"
            "\n"
            "ابتدا از بخش پروژه‌ها یک پروژه "
            "اضافه کنید.",
            reply_markup=(
                backup_projects_keyboard(
                    projects,
                )
            ),
        )

        return

    active_count = sum(1 for project in projects if project.enabled)

    await callback.message.edit_text(
        "💾 <b>تهیه بکاپ</b>\n"
        "\n"
        "پروژه مورد نظر را انتخاب کنید:\n"
        "\n"
        f"🟢 فعال: <b>{active_count}</b>\n"
        f"🔴 غیرفعال: "
        f"<b>{len(projects) - active_count}</b>\n"
        "\n"
        "پروژه‌های غیرفعال امکان تهیه بکاپ "
        "ندارند.",
        reply_markup=(
            backup_projects_keyboard(
                projects,
            )
        ),
    )
