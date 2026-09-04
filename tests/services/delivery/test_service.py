from __future__ import annotations

from datetime import (
    datetime,
    timezone,
)
from pathlib import Path
from unittest.mock import (
    AsyncMock,
)

import pytest

from django_assistant_bot.database.models.enums import (
    BackupStatus,
)
from django_assistant_bot.services.backup.models import (
    BackupResult,
    ChecksumResult,
)
from django_assistant_bot.services.delivery import (
    BackupDeliveryFileNotFoundError,
    BackupDeliveryService,
    DeliveryResult,
)


def build_result(
    tmp_path: Path,
) -> BackupResult:
    archive_path = tmp_path / "backup.zip"

    archive_path.write_bytes(b"backup")

    now = datetime.now(
        timezone.utc,
    )

    return BackupResult(
        project_id="project-1",
        project_name="Test Project",
        status=BackupStatus.SUCCESS,
        archive_path=archive_path,
        started_at=now,
        finished_at=now,
        database_size_bytes=100,
        media_size_bytes=200,
        archive_size_bytes=6,
        media_file_count=5,
        checksum=ChecksumResult(
            algorithm="sha256",
            value="checksum",
        ),
    )


@pytest.mark.asyncio
async def test_delivery_delegates_to_backend(
    tmp_path: Path,
) -> None:
    result = build_result(tmp_path)

    backend = AsyncMock()

    expected = DeliveryResult(
        attempted=1,
        succeeded=1,
        failed=0,
    )

    backend.deliver.return_value = expected

    service = BackupDeliveryService(backend)

    delivery_result = await service.deliver(result)

    assert delivery_result == expected

    backend.deliver.assert_awaited_once_with(result)


@pytest.mark.asyncio
async def test_missing_archive_is_rejected(
    tmp_path: Path,
) -> None:
    result = build_result(tmp_path)

    result.archive_path.unlink()

    backend = AsyncMock()

    service = BackupDeliveryService(backend)

    with pytest.raises(
        BackupDeliveryFileNotFoundError,
    ):
        await service.deliver(result)

    backend.deliver.assert_not_awaited()
