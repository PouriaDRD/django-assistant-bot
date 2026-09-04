from __future__ import annotations

from datetime import (
    datetime,
    timezone,
)
from pathlib import Path
from unittest.mock import (
    AsyncMock,
    Mock,
)

import pytest
from aiogram import Bot
from aiogram.types import FSInputFile

from django_assistant_bot.bot.delivery.telegram import (
    TelegramBackupDelivery,
)
from django_assistant_bot.database.models.enums import (
    BackupStatus,
)
from django_assistant_bot.schemas.admin import (
    AdminSchema,
)
from django_assistant_bot.services.backup.models import (
    BackupResult,
    ChecksumResult,
)
from django_assistant_bot.services.delivery import (
    BackupDeliveryFileTooLargeError,
)

# =========================================================
# BUILDERS
# =========================================================


def build_bot() -> Mock:
    """
    Build a mocked aiogram Bot.
    """

    bot = Mock(
        spec=Bot,
    )

    bot.send_document = AsyncMock()
    bot.send_message = AsyncMock()

    return bot


def build_admin(
    telegram_user_id: int,
) -> AdminSchema:
    """
    Build an administrator schema for delivery tests.
    """

    return AdminSchema(
        telegram_user_id=telegram_user_id,
        created_at=datetime.now(
            timezone.utc,
        ),
    )


def build_result(
    tmp_path: Path,
    *,
    project_name: str = "Test Project",
    archive_size: int = 1024,
) -> BackupResult:
    """
    Build a successful backup result with a real archive file.
    """

    archive_path = tmp_path / "backup.zip"

    archive_path.write_bytes(b"x" * archive_size)

    now = datetime.now(
        timezone.utc,
    )

    return BackupResult(
        project_id="project-1",
        project_name=project_name,
        status=BackupStatus.SUCCESS,
        archive_path=archive_path,
        started_at=now,
        finished_at=now,
        database_size_bytes=100,
        media_size_bytes=200,
        archive_size_bytes=archive_size,
        media_file_count=5,
        checksum=ChecksumResult(
            algorithm="sha256",
            value="checksum-value",
        ),
    )


def build_admin_reader(
    admins: list[AdminSchema],
) -> Mock:
    """
    Build a mocked admin reader.
    """

    reader = Mock()

    reader.list_admins.return_value = admins

    return reader


# =========================================================
# SINGLE ADMIN
# =========================================================


@pytest.mark.asyncio
async def test_delivery_sends_backup_to_single_admin(
    tmp_path: Path,
) -> None:
    result = build_result(
        tmp_path,
    )

    admin = build_admin(
        1001,
    )

    bot = build_bot()

    admins = build_admin_reader(
        [
            admin,
        ]
    )

    delivery = TelegramBackupDelivery(
        bot=bot,
        admins=admins,
    )

    delivery_result = await delivery.deliver(result)

    assert delivery_result.attempted == 1
    assert delivery_result.succeeded == 1
    assert delivery_result.failed == 0

    bot.send_document.assert_awaited_once()

    call = bot.send_document.await_args

    assert call.kwargs["chat_id"] == admin.telegram_user_id

    assert isinstance(
        call.kwargs["document"],
        FSInputFile,
    )

    assert "Test Project" in call.kwargs["caption"]


# =========================================================
# MULTIPLE ADMINS
# =========================================================


@pytest.mark.asyncio
async def test_delivery_sends_backup_to_all_admins(
    tmp_path: Path,
) -> None:
    result = build_result(
        tmp_path,
    )

    admins_list = [
        build_admin(
            1001,
        ),
        build_admin(
            1002,
        ),
        build_admin(
            1003,
        ),
    ]

    bot = build_bot()

    admins = build_admin_reader(admins_list)

    delivery = TelegramBackupDelivery(
        bot=bot,
        admins=admins,
    )

    delivery_result = await delivery.deliver(result)

    assert delivery_result.attempted == 3
    assert delivery_result.succeeded == 3
    assert delivery_result.failed == 0

    assert bot.send_document.await_count == 3


# =========================================================
# PARTIAL FAILURE
# =========================================================


@pytest.mark.asyncio
async def test_delivery_continues_when_one_admin_fails(
    tmp_path: Path,
) -> None:
    result = build_result(
        tmp_path,
    )

    admins_list = [
        build_admin(
            1001,
        ),
        build_admin(
            1002,
        ),
        build_admin(
            1003,
        ),
    ]

    bot = build_bot()

    bot.send_document.side_effect = [
        None,
        RuntimeError("telegram unavailable"),
        None,
    ]

    admins = build_admin_reader(admins_list)

    delivery = TelegramBackupDelivery(
        bot=bot,
        admins=admins,
    )

    delivery_result = await delivery.deliver(result)

    assert delivery_result.attempted == 3
    assert delivery_result.succeeded == 2
    assert delivery_result.failed == 1
    assert delivery_result.is_partial is True

    assert bot.send_document.await_count == 3


# =========================================================
# NO ADMINS
# =========================================================


@pytest.mark.asyncio
async def test_delivery_with_no_admins_returns_empty_result(
    tmp_path: Path,
) -> None:
    result = build_result(
        tmp_path,
    )

    bot = build_bot()

    admins = build_admin_reader([])

    delivery = TelegramBackupDelivery(
        bot=bot,
        admins=admins,
    )

    delivery_result = await delivery.deliver(result)

    assert delivery_result.attempted == 0
    assert delivery_result.succeeded == 0
    assert delivery_result.failed == 0

    bot.send_document.assert_not_awaited()
    bot.send_message.assert_not_awaited()


# =========================================================
# FILE TOO LARGE
# =========================================================


@pytest.mark.asyncio
async def test_large_backup_is_not_uploaded(
    tmp_path: Path,
) -> None:
    result = build_result(
        tmp_path,
        archive_size=1024,
    )

    admin = build_admin(
        1001,
    )

    bot = build_bot()

    admins = build_admin_reader(
        [
            admin,
        ]
    )

    delivery = TelegramBackupDelivery(
        bot=bot,
        admins=admins,
        max_file_size_bytes=512,
    )

    with pytest.raises(
        BackupDeliveryFileTooLargeError,
    ):
        await delivery.deliver(result)

    bot.send_document.assert_not_awaited()

    bot.send_message.assert_awaited_once()

    call = bot.send_message.await_args

    assert call.kwargs["chat_id"] == admin.telegram_user_id

    assert "بکاپ ساخته شد اما ارسال نشد" in call.kwargs["text"]


# =========================================================
# OVERSIZED NOTIFICATION FAILURE
# =========================================================


@pytest.mark.asyncio
async def test_large_backup_notification_failure_does_not_stop_other_admins(
    tmp_path: Path,
) -> None:
    result = build_result(
        tmp_path,
        archive_size=1024,
    )

    admins_list = [
        build_admin(
            1001,
        ),
        build_admin(
            1002,
        ),
    ]

    bot = build_bot()

    bot.send_message.side_effect = [
        RuntimeError("first notification failed"),
        None,
    ]

    admins = build_admin_reader(admins_list)

    delivery = TelegramBackupDelivery(
        bot=bot,
        admins=admins,
        max_file_size_bytes=512,
    )

    with pytest.raises(
        BackupDeliveryFileTooLargeError,
    ):
        await delivery.deliver(result)

    assert bot.send_message.await_count == 2

    bot.send_document.assert_not_awaited()


# =========================================================
# HTML ESCAPING
# =========================================================


@pytest.mark.asyncio
async def test_delivery_caption_escapes_project_name(
    tmp_path: Path,
) -> None:
    result = build_result(
        tmp_path,
        project_name=("<script>alert('x')</script>"),
    )

    admin = build_admin(
        1001,
    )

    bot = build_bot()

    admins = build_admin_reader(
        [
            admin,
        ]
    )

    delivery = TelegramBackupDelivery(
        bot=bot,
        admins=admins,
    )

    await delivery.deliver(result)

    call = bot.send_document.await_args

    caption = call.kwargs["caption"]

    assert "<script>" not in caption

    assert "&lt;script&gt;" in caption


# =========================================================
# CHECKSUM
# =========================================================


@pytest.mark.asyncio
async def test_delivery_caption_contains_checksum(
    tmp_path: Path,
) -> None:
    result = build_result(
        tmp_path,
    )

    admin = build_admin(
        1001,
    )

    bot = build_bot()

    admins = build_admin_reader(
        [
            admin,
        ]
    )

    delivery = TelegramBackupDelivery(
        bot=bot,
        admins=admins,
    )

    await delivery.deliver(result)

    call = bot.send_document.await_args

    caption = call.kwargs["caption"]

    assert "checksum-value" in caption

    assert "SHA256" in caption
