from __future__ import annotations

import asyncio
from datetime import (
    datetime,
    timezone,
)
from pathlib import (
    Path,
)
from typing import (
    Any,
)

import pytest
from aiogram.exceptions import (
    TelegramBadRequest,
    TelegramForbiddenError,
    TelegramNetworkError,
)
from aiogram.methods import (
    GetMe,
)

from django_assistant_bot.bot.delivery.telegram import (
    TelegramBackupDelivery,
)
from django_assistant_bot.database.models.enums import (
    BackupStatus,
)
from django_assistant_bot.schemas.admin import (
    AdminSchema,
)
from django_assistant_bot.schemas.project import (
    ProjectSchema,
)
from django_assistant_bot.services.backup.models import (
    BackupResult,
    ChecksumResult,
)
from django_assistant_bot.services.scheduler import (
    BackupSchedulerService,
)

# =========================================================
# CONFIGURATION
# =========================================================


ADMIN_COUNT = 100

SUCCESS_MODULO = 5


# =========================================================
# TEST DOUBLES
# =========================================================


class AdminReader:
    """
    Return a fixed list of Telegram administrators.
    """

    def __init__(
        self,
        admins: list[AdminSchema],
    ) -> None:
        self._admins = admins

    def list_admins(
        self,
    ) -> list[AdminSchema]:
        return list(
            self._admins,
        )


class StormBot:
    """
    Telegram bot test double.

    Delivery outcome is deterministic from chat ID:

    id % 5 == 0 -> success
    id % 5 == 1 -> forbidden
    id % 5 == 2 -> bad request
    id % 5 == 3 -> network error
    id % 5 == 4 -> unexpected error
    """

    def __init__(
        self,
    ) -> None:
        self.attempted_chat_ids: list[int] = []

        self.successful_chat_ids: list[int] = []

    async def send_document(
        self,
        *,
        chat_id: int,
        document: object,
        caption: str,
        **kwargs: Any,
    ) -> object:
        del document
        del caption
        del kwargs

        self.attempted_chat_ids.append(
            chat_id,
        )

        outcome = chat_id % SUCCESS_MODULO

        if outcome == 0:
            self.successful_chat_ids.append(
                chat_id,
            )

            return object()

        if outcome == 1:
            raise TelegramForbiddenError(
                method=GetMe(),
                message="bot was blocked",
            )

        if outcome == 2:
            raise TelegramBadRequest(
                method=GetMe(),
                message="chat not found",
            )

        if outcome == 3:
            raise TelegramNetworkError(
                method=GetMe(),
                message="network unavailable",
            )

        raise RuntimeError("unexpected delivery failure")


class DummyProjects:
    """
    Scheduler dependency unused by direct job execution.
    """

    def list_projects(
        self,
    ) -> list[ProjectSchema]:
        return []

    def get_project(
        self,
        project_id: str,
    ) -> ProjectSchema:
        raise AssertionError(("Unexpected project lookup: " f"{project_id}"))


class SuccessfulBackupRunner:
    """
    Return one already-completed successful backup.
    """

    def __init__(
        self,
        result: BackupResult,
    ) -> None:
        self.result = result

        self.call_count = 0

    def run(
        self,
        project_id: str,
    ) -> BackupResult:
        assert project_id == self.result.project_id

        self.call_count += 1

        return self.result


class ExplodingDelivery:
    """
    Delivery backend that always fails.
    """

    def __init__(
        self,
    ) -> None:
        self.call_count = 0

    async def deliver(
        self,
        result: BackupResult,
    ) -> object:
        del result

        self.call_count += 1

        raise TelegramNetworkError(
            method=GetMe(),
            message="simulated delivery outage",
        )


# =========================================================
# BUILDERS
# =========================================================


def build_admins(
    count: int = ADMIN_COUNT,
) -> list[AdminSchema]:
    now = datetime.now(
        timezone.utc,
    )

    return [
        AdminSchema(
            telegram_user_id=(10_000 + index),
            created_at=now,
        )
        for index in range(count)
    ]


def build_backup_result(
    tmp_path: Path,
) -> BackupResult:
    archive_path = tmp_path / "delivery-stress.zip"

    archive_path.write_bytes(b"delivery-stress")

    now = datetime.now(
        timezone.utc,
    )

    return BackupResult(
        project_id="delivery-project",
        project_name="Delivery Project",
        status=BackupStatus.SUCCESS,
        archive_path=archive_path,
        started_at=now,
        finished_at=now,
        database_size_bytes=1024,
        media_size_bytes=2048,
        archive_size_bytes=(archive_path.stat().st_size),
        media_file_count=10,
        checksum=ChecksumResult(
            algorithm="sha256",
            value="delivery-stress-checksum",
        ),
    )


# =========================================================
# FAILURE STORM
# =========================================================


@pytest.mark.asyncio
async def test_telegram_delivery_attempts_every_admin_during_failure_storm(
    tmp_path: Path,
) -> None:
    """
    Deliver to many administrators where most attempts fail.

    Failure for one admin must never stop later admins from
    being attempted.
    """

    admins = build_admins()

    bot = StormBot()

    result = build_backup_result(
        tmp_path,
    )

    delivery = TelegramBackupDelivery(
        bot=bot,  # type: ignore[arg-type]
        admins=AdminReader(
            admins,
        ),
    )

    delivery_result = await delivery.deliver(
        result,
    )

    # -----------------------------------------------------
    # EVERY ADMIN MUST BE ATTEMPTED
    # -----------------------------------------------------

    assert len(bot.attempted_chat_ids) == ADMIN_COUNT

    assert set(bot.attempted_chat_ids) == {admin.telegram_user_id for admin in admins}

    # -----------------------------------------------------
    # EXPECTED SUCCESS / FAILURE COUNTS
    # -----------------------------------------------------

    expected_successes = sum(
        1 for admin in admins if (admin.telegram_user_id % SUCCESS_MODULO == 0)
    )

    expected_failures = ADMIN_COUNT - expected_successes

    assert delivery_result.attempted == ADMIN_COUNT

    assert delivery_result.succeeded == expected_successes

    assert delivery_result.failed == expected_failures

    assert len(bot.successful_chat_ids) == expected_successes


# =========================================================
# DELIVERY STORM REPEATABILITY
# =========================================================


@pytest.mark.asyncio
async def test_repeated_delivery_storms_do_not_poison_delivery_instance(
    tmp_path: Path,
) -> None:
    """
    Run repeated mixed-failure delivery rounds through the
    same TelegramBackupDelivery instance.

    Earlier failures must not poison future delivery calls.
    """

    admins = build_admins()

    bot = StormBot()

    result = build_backup_result(
        tmp_path,
    )

    delivery = TelegramBackupDelivery(
        bot=bot,  # type: ignore[arg-type]
        admins=AdminReader(
            admins,
        ),
    )

    rounds = 20

    expected_successes_per_round = sum(
        1 for admin in admins if (admin.telegram_user_id % SUCCESS_MODULO == 0)
    )

    for _ in range(rounds):
        delivery_result = await delivery.deliver(
            result,
        )

        assert delivery_result.attempted == ADMIN_COUNT

        assert delivery_result.succeeded == expected_successes_per_round

        assert delivery_result.failed == (ADMIN_COUNT - expected_successes_per_round)

    assert len(bot.attempted_chat_ids) == (ADMIN_COUNT * rounds)

    assert len(bot.successful_chat_ids) == (expected_successes_per_round * rounds)


# =========================================================
# CONCURRENT DELIVERY STORMS
# =========================================================


@pytest.mark.asyncio
async def test_multiple_delivery_storms_can_run_concurrently(
    tmp_path: Path,
) -> None:
    """
    Run several delivery operations concurrently.

    Each operation must independently account for all admins.
    """

    admins = build_admins()

    result = build_backup_result(
        tmp_path,
    )

    delivery_count = 10

    deliveries: list[TelegramBackupDelivery] = []

    bots: list[StormBot] = []

    for _ in range(delivery_count):
        bot = StormBot()

        bots.append(bot)

        deliveries.append(
            TelegramBackupDelivery(
                bot=bot,  # type: ignore[arg-type]
                admins=AdminReader(
                    admins,
                ),
            )
        )

    results = await asyncio.gather(
        *[
            delivery.deliver(
                result,
            )
            for delivery in deliveries
        ],
    )

    assert len(results) == delivery_count

    for delivery_result in results:
        assert delivery_result.attempted == ADMIN_COUNT

        assert delivery_result.succeeded + delivery_result.failed == ADMIN_COUNT

    for bot in bots:
        assert len(bot.attempted_chat_ids) == ADMIN_COUNT


# =========================================================
# SCHEDULER DELIVERY FAILURE ISOLATION
# =========================================================


@pytest.mark.asyncio
async def test_scheduler_keeps_successful_backup_successful_when_delivery_fails(
    tmp_path: Path,
) -> None:
    """
    A successful backup must remain successful even when the
    delivery layer raises a transport failure.

    Scheduler must absorb delivery exceptions instead of
    propagating them as backup failures.
    """

    result = build_backup_result(
        tmp_path,
    )

    backups = SuccessfulBackupRunner(
        result,
    )

    delivery = ExplodingDelivery()

    service = BackupSchedulerService(
        projects=DummyProjects(),
        backups=backups,
    )

    service.set_delivery(
        delivery,
    )

    await service._run_project_backup(
        result.project_id,
    )

    assert backups.call_count == 1

    assert delivery.call_count == 1

    # The archive created by the successful backup result
    # must remain intact. Delivery failure must not mutate
    # or delete it.
    assert result.archive_path.exists()

    assert result.archive_path.read_bytes() == b"delivery-stress"


# =========================================================
# MASSIVE SCHEDULER DELIVERY FAILURE STORM
# =========================================================


@pytest.mark.asyncio
async def test_scheduler_survives_many_delivery_failures(
    tmp_path: Path,
) -> None:
    """
    Repeated delivery exceptions must not poison scheduler
    execution.

    Every scheduled backup succeeds independently while each
    delivery attempt fails.
    """

    result = build_backup_result(
        tmp_path,
    )

    backups = SuccessfulBackupRunner(
        result,
    )

    delivery = ExplodingDelivery()

    service = BackupSchedulerService(
        projects=DummyProjects(),
        backups=backups,
    )

    service.set_delivery(
        delivery,
    )

    executions = 100

    for _ in range(executions):
        await service._run_project_backup(
            result.project_id,
        )

    assert backups.call_count == (executions)

    assert delivery.call_count == (executions)

    assert result.archive_path.exists()
