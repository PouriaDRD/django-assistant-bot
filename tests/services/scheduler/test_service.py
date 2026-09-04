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
from apscheduler.schedulers.asyncio import (
    AsyncIOScheduler,
)

from django_assistant_bot.database.models.enums import (
    BackupStatus,
    DatabaseType,
    ScheduleUnit,
)
from django_assistant_bot.schemas.project import (
    DatabaseSchema,
    MediaSchema,
    ProjectSchema,
    ScheduleSchema,
)
from django_assistant_bot.services.backup.models import (
    BackupResult,
    ChecksumResult,
)
from django_assistant_bot.services.delivery.models import (
    DeliveryResult,
)
from django_assistant_bot.services.scheduler import (
    JOB_PREFIX,
    BackupSchedulerService,
)

# =========================================================
# TEST DOUBLES
# =========================================================


class FakeDelivery:
    """
    Test double compatible with the scheduler's
    BackupDelivery protocol.
    """

    def __init__(
        self,
        *,
        error: Exception | None = None,
    ) -> None:
        self.deliver = AsyncMock(
            side_effect=error,
            return_value=DeliveryResult(
                attempted=1,
                succeeded=1,
                failed=0,
            ),
        )


# =========================================================
# BUILDERS
# =========================================================


def build_project(
    tmp_path: Path,
    *,
    project_id: str = "project-1",
    enabled: bool = True,
    schedule_enabled: bool = True,
    interval: int = 1,
    unit: ScheduleUnit = ScheduleUnit.HOURS,
) -> ProjectSchema:
    return ProjectSchema(
        id=project_id,
        name="Test Project",
        enabled=enabled,
        database=DatabaseSchema(
            type=DatabaseType.SQLITE,
            path=(tmp_path / "db.sqlite3"),
        ),
        media=MediaSchema(
            enabled=False,
            path=(tmp_path / "media"),
        ),
        schedule=ScheduleSchema(
            enabled=schedule_enabled,
            interval=interval,
            unit=unit,
        ),
    )


def build_service(
    *,
    projects: Mock | None = None,
    backups: Mock | None = None,
    scheduler: Mock | None = None,
) -> BackupSchedulerService:
    return BackupSchedulerService(
        projects=(projects if projects is not None else Mock()),
        backups=(backups if backups is not None else Mock()),
        scheduler=(
            scheduler
            if scheduler is not None
            else Mock(
                spec=AsyncIOScheduler,
            )
        ),
    )


def build_backup_result(
    tmp_path: Path,
) -> BackupResult:
    archive_path = tmp_path / "scheduled-backup.zip"

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
            value="checksum-value",
        ),
    )


# =========================================================
# SCHEDULER SYNC
# =========================================================


def test_sync_project_adds_enabled_schedule(
    tmp_path: Path,
) -> None:
    scheduler = Mock(
        spec=AsyncIOScheduler,
    )

    project = build_project(
        tmp_path,
        interval=3,
        unit=ScheduleUnit.HOURS,
    )

    service = build_service(
        scheduler=scheduler,
    )

    service.sync_project(project)

    scheduler.add_job.assert_called_once()

    call = scheduler.add_job.call_args

    assert call.kwargs["id"] == f"{JOB_PREFIX}{project.id}"

    assert call.kwargs["replace_existing"] is True

    assert call.kwargs["coalesce"] is True

    assert call.kwargs["max_instances"] == 1


@pytest.mark.parametrize(
    (
        "enabled",
        "schedule_enabled",
    ),
    [
        (
            False,
            True,
        ),
        (
            True,
            False,
        ),
        (
            False,
            False,
        ),
    ],
)
def test_sync_project_removes_disabled_schedule(
    tmp_path: Path,
    enabled: bool,
    schedule_enabled: bool,
) -> None:
    scheduler = Mock(
        spec=AsyncIOScheduler,
    )

    project = build_project(
        tmp_path,
        enabled=enabled,
        schedule_enabled=schedule_enabled,
    )

    service = build_service(
        scheduler=scheduler,
    )

    service.sync_project(project)

    scheduler.add_job.assert_not_called()

    scheduler.remove_job.assert_called_once_with(f"{JOB_PREFIX}{project.id}")


@pytest.mark.parametrize(
    "unit",
    [
        ScheduleUnit.MINUTES,
        ScheduleUnit.HOURS,
        ScheduleUnit.DAYS,
    ],
)
def test_supported_schedule_units(
    tmp_path: Path,
    unit: ScheduleUnit,
) -> None:
    scheduler = Mock(
        spec=AsyncIOScheduler,
    )

    project = build_project(
        tmp_path,
        unit=unit,
    )

    service = build_service(
        scheduler=scheduler,
    )

    service.sync_project(project)

    scheduler.add_job.assert_called_once()


# =========================================================
# LIFECYCLE
# =========================================================


def test_start_restores_jobs(
    tmp_path: Path,
) -> None:
    project = build_project(
        tmp_path,
    )

    projects = Mock()

    projects.list_projects.return_value = [
        project,
    ]

    scheduler = Mock(
        spec=AsyncIOScheduler,
    )

    scheduler.get_jobs.return_value = []

    service = build_service(
        projects=projects,
        scheduler=scheduler,
    )

    service.start()

    scheduler.start.assert_called_once_with()

    projects.list_projects.assert_called_once_with()

    scheduler.add_job.assert_called_once()


def test_start_is_idempotent() -> None:
    projects = Mock()

    projects.list_projects.return_value = []

    scheduler = Mock(
        spec=AsyncIOScheduler,
    )

    scheduler.get_jobs.return_value = []

    service = build_service(
        projects=projects,
        scheduler=scheduler,
    )

    service.start()
    service.start()

    scheduler.start.assert_called_once_with()


def test_stop_is_idempotent() -> None:
    projects = Mock()

    projects.list_projects.return_value = []

    scheduler = Mock(
        spec=AsyncIOScheduler,
    )

    scheduler.get_jobs.return_value = []

    service = build_service(
        projects=projects,
        scheduler=scheduler,
    )

    service.start()

    service.stop()
    service.stop()

    scheduler.shutdown.assert_called_once_with(
        wait=False,
    )


# =========================================================
# BACKUP EXECUTION
# =========================================================


@pytest.mark.asyncio
async def test_scheduled_job_runs_backup_in_thread(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    backups = Mock()

    service = build_service(
        backups=backups,
    )

    to_thread = AsyncMock()

    monkeypatch.setattr(
        ("django_assistant_bot.services.scheduler.service." "asyncio.to_thread"),
        to_thread,
    )

    await service._run_project_backup("project-1")

    to_thread.assert_awaited_once_with(
        backups.run,
        "project-1",
    )


# =========================================================
# DELIVERY INTEGRATION
# =========================================================


@pytest.mark.asyncio
async def test_scheduled_backup_delivers_result(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result = build_backup_result(
        tmp_path,
    )

    backups = Mock()

    delivery = FakeDelivery()

    service = build_service(
        backups=backups,
    )

    service.set_delivery(
        delivery,
    )

    to_thread = AsyncMock(
        return_value=result,
    )

    monkeypatch.setattr(
        ("django_assistant_bot.services.scheduler.service." "asyncio.to_thread"),
        to_thread,
    )

    await service._run_project_backup(
        result.project_id,
    )

    to_thread.assert_awaited_once_with(
        backups.run,
        result.project_id,
    )

    delivery.deliver.assert_awaited_once_with(
        result,
    )


@pytest.mark.asyncio
async def test_scheduled_backup_survives_delivery_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result = build_backup_result(
        tmp_path,
    )

    backups = Mock()

    delivery = FakeDelivery(
        error=RuntimeError("delivery failed"),
    )

    service = build_service(
        backups=backups,
    )

    service.set_delivery(
        delivery,
    )

    to_thread = AsyncMock(
        return_value=result,
    )

    monkeypatch.setattr(
        ("django_assistant_bot.services.scheduler.service." "asyncio.to_thread"),
        to_thread,
    )

    # Delivery failure must not escape from the scheduler job.
    await service._run_project_backup(
        result.project_id,
    )

    to_thread.assert_awaited_once_with(
        backups.run,
        result.project_id,
    )

    delivery.deliver.assert_awaited_once_with(
        result,
    )
