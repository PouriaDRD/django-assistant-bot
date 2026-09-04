from __future__ import annotations

import asyncio
from datetime import (
    datetime,
    timezone,
)
from pathlib import (
    Path,
)
from threading import (
    Event,
    Lock,
)

import pytest

from django_assistant_bot.database.models.enums import (
    BackupStatus,
)
from django_assistant_bot.schemas.project import (
    ProjectSchema,
)
from django_assistant_bot.services.backup import (
    BackupAlreadyRunningError,
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


OVERLAP_REQUEST_COUNT = 64

WAIT_TIMEOUT_SECONDS = 10.0


# =========================================================
# TEST DOUBLES
# =========================================================


class DummyProjects:
    """
    Minimal project dependency for scheduler stress tests.

    This class intentionally provides no actual projects
    because these tests execute scheduler jobs directly.
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


class BlockingBackupCoordinator:
    """
    Simulate BackupCoordinator same-project locking.

    The first invocation enters and blocks.

    Every concurrent invocation for the same project
    raises BackupAlreadyRunningError immediately.
    """

    def __init__(
        self,
        result: BackupResult,
    ) -> None:
        self._result = result

        self._state_lock = Lock()

        self._running = False

        self.entered = Event()

        self.release = Event()

        self.success_count = 0

        self.rejected_count = 0

        self.total_calls = 0

    def run(
        self,
        project_id: str,
    ) -> BackupResult:
        with self._state_lock:
            self.total_calls += 1

            if self._running:
                self.rejected_count += 1

                raise BackupAlreadyRunningError(
                    ("Backup is already running " f"for project {project_id}.")
                )

            self._running = True

        self.entered.set()

        try:
            if not self.release.wait(
                timeout=WAIT_TIMEOUT_SECONDS,
            ):
                raise RuntimeError(
                    ("Timed out waiting for scheduler " "stress-test release.")
                )

            with self._state_lock:
                self.success_count += 1

            return self._result

        finally:
            with self._state_lock:
                self._running = False


class CountingDelivery:
    """
    Count successful scheduled deliveries.
    """

    def __init__(
        self,
    ) -> None:
        self._lock = asyncio.Lock()

        self.call_count = 0

        self.project_ids: list[str] = []

    async def deliver(
        self,
        result: BackupResult,
    ) -> object:
        async with self._lock:
            self.call_count += 1

            self.project_ids.append(
                result.project_id,
            )

        return object()


# =========================================================
# BUILDERS
# =========================================================


def build_result(
    tmp_path: Path,
) -> BackupResult:
    now = datetime.now(
        timezone.utc,
    )

    archive_path = tmp_path / "scheduled-stress.zip"

    archive_path.write_bytes(b"stress")

    return BackupResult(
        project_id="project-1",
        project_name="Stress Project",
        status=BackupStatus.SUCCESS,
        archive_path=archive_path,
        started_at=now,
        finished_at=now,
        database_size_bytes=1024,
        media_size_bytes=2048,
        archive_size_bytes=6,
        media_file_count=5,
        checksum=ChecksumResult(
            algorithm="sha256",
            value="scheduler-stress-checksum",
        ),
    )


# =========================================================
# SAME PROJECT OVERLAP
# =========================================================


@pytest.mark.asyncio
async def test_scheduler_overlap_allows_only_one_same_project_backup(
    tmp_path: Path,
) -> None:
    """
    Call the scheduler execution path many times concurrently
    for the same project.

    Expected:

    - exactly one backup invocation succeeds
    - every overlapping invocation is rejected
    - scheduler absorbs BackupAlreadyRunningError
    - only the successful backup reaches delivery
    - no task leaks or propagates an exception
    """

    result = build_result(
        tmp_path,
    )

    backups = BlockingBackupCoordinator(
        result,
    )

    delivery = CountingDelivery()

    service = BackupSchedulerService(
        projects=DummyProjects(),
        backups=backups,
    )

    service.set_delivery(
        delivery,
    )

    # -----------------------------------------------------
    # START FIRST SCHEDULED BACKUP
    # -----------------------------------------------------

    first_task = asyncio.create_task(
        service._run_project_backup(
            result.project_id,
        )
    )

    entered = await asyncio.to_thread(
        backups.entered.wait,
        WAIT_TIMEOUT_SECONDS,
    )

    assert entered is True

    # -----------------------------------------------------
    # CREATE LARGE OVERLAP STORM
    # -----------------------------------------------------

    overlapping_tasks = [
        asyncio.create_task(
            service._run_project_backup(
                result.project_id,
            )
        )
        for _ in range(OVERLAP_REQUEST_COUNT)
    ]

    await asyncio.gather(
        *overlapping_tasks,
    )

    # All overlapping executions should already have
    # returned after BackupAlreadyRunningError was handled.
    assert backups.rejected_count == (OVERLAP_REQUEST_COUNT)

    assert backups.success_count == 0

    assert backups.total_calls == (OVERLAP_REQUEST_COUNT + 1)

    # The first backup has not completed yet, therefore
    # delivery must not have happened.
    assert delivery.call_count == 0

    # -----------------------------------------------------
    # RELEASE THE WINNING BACKUP
    # -----------------------------------------------------

    backups.release.set()

    await asyncio.wait_for(
        first_task,
        timeout=WAIT_TIMEOUT_SECONDS,
    )

    # -----------------------------------------------------
    # FINAL INVARIANTS
    # -----------------------------------------------------

    assert backups.total_calls == (OVERLAP_REQUEST_COUNT + 1)

    assert backups.success_count == 1

    assert backups.rejected_count == (OVERLAP_REQUEST_COUNT)

    assert delivery.call_count == 1

    assert delivery.project_ids == [
        result.project_id,
    ]


# =========================================================
# EVENT LOOP RESPONSIVENESS
# =========================================================


@pytest.mark.asyncio
async def test_scheduled_backup_does_not_block_event_loop(
    tmp_path: Path,
) -> None:
    """
    Verify the synchronous backup execution remains outside
    the asyncio event loop through asyncio.to_thread().
    """

    result = build_result(
        tmp_path,
    )

    backups = BlockingBackupCoordinator(
        result,
    )

    service = BackupSchedulerService(
        projects=DummyProjects(),
        backups=backups,
    )

    scheduled_task = asyncio.create_task(
        service._run_project_backup(
            result.project_id,
        )
    )

    entered = await asyncio.to_thread(
        backups.entered.wait,
        WAIT_TIMEOUT_SECONDS,
    )

    assert entered is True

    # -----------------------------------------------------
    # HEARTBEAT
    # -----------------------------------------------------

    heartbeat_count = 0

    async def heartbeat() -> None:
        nonlocal heartbeat_count

        for _ in range(
            100,
        ):
            heartbeat_count += 1

            await asyncio.sleep(
                0,
            )

    await asyncio.wait_for(
        heartbeat(),
        timeout=1,
    )

    # If BackupCoordinator.run() were executed directly on
    # the event loop, this heartbeat could not complete while
    # the backup runner is blocked.
    assert heartbeat_count == 100

    # -----------------------------------------------------
    # FINISH BACKUP
    # -----------------------------------------------------

    backups.release.set()

    await asyncio.wait_for(
        scheduled_task,
        timeout=WAIT_TIMEOUT_SECONDS,
    )

    assert backups.success_count == 1


# =========================================================
# MULTI PROJECT EXECUTION
# =========================================================


class MultiProjectBlockingCoordinator:
    """
    Track simultaneous scheduler execution across projects.
    """

    def __init__(
        self,
        *,
        project_count: int,
        tmp_path: Path,
    ) -> None:
        self._project_count = project_count

        self._tmp_path = tmp_path

        self._lock = Lock()

        self._release = Event()

        self.all_entered = Event()

        self.entered_project_ids: set[str] = set()

        self.max_concurrent = 0

        self._current_concurrent = 0

    @property
    def release(
        self,
    ) -> Event:
        return self._release

    def run(
        self,
        project_id: str,
    ) -> BackupResult:
        with self._lock:
            self.entered_project_ids.add(
                project_id,
            )

            self._current_concurrent += 1

            self.max_concurrent = max(
                self.max_concurrent,
                self._current_concurrent,
            )

            if len(self.entered_project_ids) == self._project_count:
                self.all_entered.set()

        try:
            if not self._release.wait(
                timeout=WAIT_TIMEOUT_SECONDS,
            ):
                raise RuntimeError(
                    ("Timed out waiting for multi-project " "scheduler release.")
                )

            now = datetime.now(
                timezone.utc,
            )

            archive_path = self._tmp_path / f"{project_id}.zip"

            archive_path.write_bytes(b"stress")

            return BackupResult(
                project_id=project_id,
                project_name=project_id,
                status=BackupStatus.SUCCESS,
                archive_path=archive_path,
                started_at=now,
                finished_at=now,
                database_size_bytes=1,
                media_size_bytes=0,
                archive_size_bytes=6,
                media_file_count=0,
                checksum=ChecksumResult(
                    algorithm="sha256",
                    value=(f"checksum-{project_id}"),
                ),
            )

        finally:
            with self._lock:
                self._current_concurrent -= 1


@pytest.mark.asyncio
async def test_scheduler_allows_different_projects_to_execute_concurrently(
    tmp_path: Path,
) -> None:
    """
    Different scheduled projects must not become serialized
    by the scheduler service execution path.
    """

    project_count = 16

    backups = MultiProjectBlockingCoordinator(
        project_count=project_count,
        tmp_path=tmp_path,
    )

    service = BackupSchedulerService(
        projects=DummyProjects(),
        backups=backups,
    )

    tasks = [
        asyncio.create_task(
            service._run_project_backup(
                f"project-{index}",
            )
        )
        for index in range(project_count)
    ]

    entered = await asyncio.to_thread(
        backups.all_entered.wait,
        WAIT_TIMEOUT_SECONDS,
    )

    assert entered is True

    assert len(backups.entered_project_ids) == project_count

    # They genuinely overlapped instead of running one by one.
    assert backups.max_concurrent > 1

    backups.release.set()

    await asyncio.wait_for(
        asyncio.gather(
            *tasks,
        ),
        timeout=WAIT_TIMEOUT_SECONDS,
    )

    assert backups.entered_project_ids == {
        f"project-{index}" for index in range(project_count)
    }
