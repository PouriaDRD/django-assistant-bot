from __future__ import annotations

import logging
from pathlib import Path
from typing import Protocol

from django_assistant_bot.services.backup.models import (
    BackupResult,
)
from django_assistant_bot.services.delivery.exceptions import (
    BackupDeliveryFileNotFoundError,
)
from django_assistant_bot.services.delivery.models import (
    DeliveryResult,
)

logger = logging.getLogger(
    __name__,
)


class BackupDeliveryBackend(Protocol):
    """
    Transport-independent backup delivery contract.
    """

    async def deliver(
        self,
        result: BackupResult,
    ) -> DeliveryResult: ...


class BackupDeliveryService:
    """
    Application service for delivering completed backups.
    """

    def __init__(
        self,
        backend: BackupDeliveryBackend,
    ) -> None:
        self._backend = backend

    async def deliver(
        self,
        result: BackupResult,
    ) -> DeliveryResult:
        """
        Deliver a completed backup through configured backend.
        """

        archive_path = Path(result.archive_path)

        if not archive_path.is_file():
            raise BackupDeliveryFileNotFoundError(
                "Backup archive does not exist: " f"{archive_path}"
            )

        logger.info(
            "Delivering backup for project %s.",
            result.project_id,
        )

        delivery_result = await self._backend.deliver(result)

        logger.info(
            "Backup delivery completed for project %s: "
            "attempted=%s succeeded=%s failed=%s skipped=%s.",
            result.project_id,
            delivery_result.attempted,
            delivery_result.succeeded,
            delivery_result.failed,
            delivery_result.skipped,
        )

        return delivery_result
