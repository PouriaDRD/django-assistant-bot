from __future__ import annotations

import logging
from html import escape
from pathlib import Path
from typing import Protocol

from aiogram import Bot
from aiogram.exceptions import (
    TelegramAPIError,
)
from aiogram.types import (
    FSInputFile,
)

from django_assistant_bot.schemas.admin import (
    AdminSchema,
)
from django_assistant_bot.services.backup.models import (
    BackupResult,
)
from django_assistant_bot.services.delivery import (
    BackupDeliveryFileTooLargeError,
    DeliveryResult,
)
from django_assistant_bot.utils.formatters import (
    format_size,
)

logger = logging.getLogger(
    __name__,
)


# Standard Telegram Bot API multipart upload limit.
TELEGRAM_DOCUMENT_MAX_BYTES = 50 * 1024 * 1024


class AdminReader(Protocol):
    """
    Minimal administrator service contract.
    """

    def list_admins(
        self,
    ) -> list[AdminSchema]: ...


class TelegramBackupDelivery:
    """
    Deliver scheduled backup archives to Telegram admins.

    Failure for one administrator does not prevent delivery
    to remaining administrators.
    """

    def __init__(
        self,
        *,
        bot: Bot,
        admins: AdminReader,
        max_file_size_bytes: int = TELEGRAM_DOCUMENT_MAX_BYTES,
    ) -> None:
        self._bot = bot

        self._admins = admins

        self._max_file_size_bytes = max_file_size_bytes

    async def deliver(
        self,
        result: BackupResult,
    ) -> DeliveryResult:
        """
        Send backup archive to every configured administrator.
        """

        archive_path = Path(result.archive_path)

        archive_size = archive_path.stat().st_size

        admins = self._admins.list_admins()

        if not admins:
            logger.warning(
                "Backup %s has no Telegram administrators " "to receive it.",
                result.project_id,
            )

            return DeliveryResult(
                attempted=0,
                succeeded=0,
                failed=0,
                skipped=0,
            )

        if archive_size > self._max_file_size_bytes:
            await self._notify_file_too_large(
                admins=admins,
                result=result,
                archive_size=archive_size,
            )

            raise BackupDeliveryFileTooLargeError(
                "Backup archive exceeds Telegram "
                f"upload limit: {archive_size} bytes."
            )

        succeeded = 0
        failed = 0

        caption = self._build_caption(result)

        for admin in admins:
            try:
                await self._bot.send_document(
                    chat_id=(admin.telegram_user_id),
                    document=FSInputFile(archive_path),
                    caption=caption,
                )

            except TelegramAPIError:
                failed += 1

                logger.exception(
                    "Could not deliver backup for project %s " "to Telegram admin %s.",
                    result.project_id,
                    admin.telegram_user_id,
                )

            except Exception:
                failed += 1

                logger.exception(
                    "Unexpected Telegram delivery failure for "
                    "project %s and admin %s.",
                    result.project_id,
                    admin.telegram_user_id,
                )

            else:
                succeeded += 1

                logger.info(
                    "Backup for project %s delivered to " "Telegram admin %s.",
                    result.project_id,
                    admin.telegram_user_id,
                )

        return DeliveryResult(
            attempted=len(admins),
            succeeded=succeeded,
            failed=failed,
        )

    async def _notify_file_too_large(
        self,
        *,
        admins: list[AdminSchema],
        result: BackupResult,
        archive_size: int,
    ) -> None:
        """
        Notify admins when Telegram cannot upload the archive.
        """

        message = (
            "⚠️ <b>بکاپ ساخته شد اما ارسال نشد</b>\n"
            "\n"
            f"📦 پروژه: <b>"
            f"{escape(result.project_name, quote=True)}"
            "</b>\n"
            f"🗜 حجم فایل: <b>"
            f"{format_size(archive_size)}"
            "</b>\n"
            f"🚫 سقف Telegram: <b>"
            f"{format_size(self._max_file_size_bytes)}"
            "</b>\n"
            "\n"
            "فایل بکاپ روی سرور ذخیره شده است."
        )

        for admin in admins:
            try:
                await self._bot.send_message(
                    chat_id=(admin.telegram_user_id),
                    text=message,
                )

            except Exception:
                logger.exception(
                    "Could not notify Telegram admin %s about " "oversized backup.",
                    admin.telegram_user_id,
                )

    @staticmethod
    def _build_caption(
        result: BackupResult,
    ) -> str:
        """
        Build Telegram backup document caption.
        """

        project_name = escape(
            result.project_name,
            quote=True,
        )

        checksum = escape(
            result.checksum.value,
            quote=True,
        )

        return (
            "✅ <b>بکاپ خودکار با موفقیت انجام شد</b>\n"
            "\n"
            f"📦 پروژه: <b>{project_name}</b>\n"
            f"🗄 دیتابیس: "
            f"<b>{format_size(result.database_size_bytes)}</b>\n"
            f"📁 مدیا: "
            f"<b>{format_size(result.media_size_bytes)}</b>\n"
            f"🗜 آرشیو: "
            f"<b>{format_size(result.archive_size_bytes)}</b>\n"
            f"📄 فایل‌های مدیا: "
            f"<b>{result.media_file_count:,}</b>\n"
            f"⏱ مدت: "
            f"<b>{result.duration_text}</b>\n"
            "\n"
            "🔐 <b>SHA256</b>\n"
            f"<code>{checksum}</code>"
        )
