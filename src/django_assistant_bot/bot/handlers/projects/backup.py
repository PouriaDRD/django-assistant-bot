from __future__ import annotations

import asyncio
import logging

from aiogram import (
    F,
    Router,
)
from aiogram.types import (
    CallbackQuery,
    FSInputFile,
    Message,
)

from django_assistant_bot.bot.context import (
    ApplicationContext,
)
from django_assistant_bot.bot.formatters.backup import (
    format_backup_failed,
    format_backup_started,
    format_backup_success,
)
from django_assistant_bot.bot.keyboards.projects import (
    project_details_keyboard,
)
from django_assistant_bot.services.backup import (
    BackupAlreadyRunningError,
    BackupDisabledError,
    BackupExecutionError,
    BackupHistoryError,
    ProjectBackupDisabledError,
)
from django_assistant_bot.services.project import (
    ProjectNotFoundError,
)

logger = logging.getLogger(
    __name__,
)


router = Router(
    name="projects.backup",
)


@router.callback_query(
    F.data.startswith("project:backup:"),
)
async def project_backup_callback(
    callback: CallbackQuery,
    context: ApplicationContext,
) -> None:
    """
    Run an immediate backup for a project.

    Backup work is synchronous and filesystem-heavy, so it
    is executed in a worker thread to avoid blocking the
    aiogram event loop.
    """

    callback_data = callback.data

    if not callback_data:
        await callback.answer()

        return

    project_id = callback_data.removeprefix("project:backup:").strip()

    if not project_id:
        await callback.answer(
            "شناسه پروژه نامعتبر است.",
            show_alert=True,
        )

        return

    # -----------------------------------------------------
    # PROJECT
    # -----------------------------------------------------

    try:
        project = context.projects.get_project(
            project_id,
        )

    except ProjectNotFoundError:
        await callback.answer(
            "پروژه پیدا نشد.",
            show_alert=True,
        )

        return

    # -----------------------------------------------------
    # ACKNOWLEDGE CALLBACK
    # -----------------------------------------------------

    await callback.answer(
        "تهیه بکاپ شروع شد.",
    )

    message = callback.message

    if not isinstance(
        message,
        Message,
    ):
        return

    # -----------------------------------------------------
    # PROGRESS MESSAGE
    # -----------------------------------------------------

    await message.edit_text(
        format_backup_started(
            project.name,
        ),
    )

    # -----------------------------------------------------
    # RUN BACKUP
    # -----------------------------------------------------

    try:
        result = await asyncio.to_thread(
            context.backups.run,
            project.id,
        )

    except ProjectBackupDisabledError:
        await message.edit_text(
            "🔴 <b>پروژه غیرفعال است.</b>\n"
            "\n"
            f"پروژه <b>{project.name}</b> در حال حاضر "
            "غیرفعال است و امکان تهیه بکاپ از آن وجود ندارد.\n"
            "\n"
            "ابتدا پروژه را فعال کنید و سپس دوباره "
            "بکاپ بگیرید.",
            reply_markup=(
                project_details_keyboard(
                    project.id,
                    project.enabled,
                )
            ),
        )

        return

    except BackupDisabledError:
        await message.edit_text(
            "⛔ <b>سیستم بکاپ غیرفعال است.</b>\n"
            "\n"
            "ابتدا بکاپ را از تنظیمات برنامه فعال کنید.",
            reply_markup=(
                project_details_keyboard(
                    project.id,
                    project.enabled,
                )
            ),
        )

        return

    except BackupAlreadyRunningError:
        await message.edit_text(
            "⏳ <b>بکاپ در حال اجراست.</b>\n"
            "\n"
            "برای این پروژه یک عملیات بکاپ دیگر "
            "در حال اجراست.",
            reply_markup=(
                project_details_keyboard(
                    project.id,
                    project.enabled,
                )
            ),
        )

        return

    except BackupHistoryError:
        logger.exception(
            "Backup completed but history " "persistence failed. project_id=%s",
            project.id,
        )

        await message.edit_text(
            "⚠️ <b>بکاپ ساخته شد اما ثبت تاریخچه "
            "ناموفق بود.</b>\n"
            "\n"
            "فایل بکاپ روی سرور ایجاد شده است، "
            "اما عملیات به‌طور کامل ثبت نشد.",
            reply_markup=(
                project_details_keyboard(
                    project.id,
                    project.enabled,
                )
            ),
        )

        return

    except BackupExecutionError:
        logger.exception(
            "Backup failed. project_id=%s",
            project.id,
        )

        await message.edit_text(
            format_backup_failed(
                project.name,
            ),
            reply_markup=(
                project_details_keyboard(
                    project.id,
                    project.enabled,
                )
            ),
        )

        return

    # -----------------------------------------------------
    # VERIFY ARCHIVE
    # -----------------------------------------------------

    if not result.archive_path.exists():
        logger.error(
            "Backup archive does not exist after "
            "successful backup. project_id=%s path=%s",
            project.id,
            result.archive_path,
        )

        await message.edit_text(
            "❌ <b>فایل بکاپ پیدا نشد.</b>\n"
            "\n"
            "عملیات بکاپ انجام شده اما فایل نهایی "
            "در مسیر مورد انتظار وجود ندارد.",
            reply_markup=(
                project_details_keyboard(
                    project.id,
                    project.enabled,
                )
            ),
        )

        return

    # -----------------------------------------------------
    # SEND ARCHIVE
    # -----------------------------------------------------

    document = FSInputFile(
        result.archive_path,
        filename=(result.archive_path.name),
    )

    try:
        await message.answer_document(
            document=document,
            caption=format_backup_success(
                result,
            ),
        )

    except Exception:
        logger.exception(
            "Failed to send backup archive " "to Telegram. project_id=%s path=%s",
            project.id,
            result.archive_path,
        )

        await message.edit_text(
            "⚠️ <b>بکاپ با موفقیت ساخته شد اما "
            "ارسال فایل به تلگرام ناموفق بود.</b>\n"
            "\n"
            "فایل بکاپ روی سرور محفوظ است.",
            reply_markup=(
                project_details_keyboard(
                    project.id,
                    project.enabled,
                )
            ),
        )

        return

    # -----------------------------------------------------
    # RESTORE PROJECT DETAILS
    # -----------------------------------------------------

    await message.edit_text(
        format_backup_success(
            result,
        ),
        reply_markup=(
            project_details_keyboard(
                project.id,
                project.enabled,
            )
        ),
    )
