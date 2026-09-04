from __future__ import annotations

from datetime import (
    datetime,
    timezone,
)
from pathlib import (
    Path,
)
from threading import (
    Barrier,
    Event,
    Lock,
    Thread,
)

from django_assistant_bot.database.models.enums import (
    BackupStatus,
    DatabaseType,
    ScheduleUnit,
)
from django_assistant_bot.schemas.app_settings import (
    AppSettingsSchema,
)
from django_assistant_bot.schemas.backup import (
    BackupHistoryCreateSchema,
    BackupHistorySchema,
)
from django_assistant_bot.schemas.project import (
    DatabaseSchema,
    MediaSchema,
    ProjectSchema,
    ScheduleSchema,
)
from django_assistant_bot.services.backup import (
    BackupAlreadyRunningError,
    BackupCoordinator,
)
from django_assistant_bot.services.backup.models import (
    BackupResult,
    ChecksumResult,
)
from django_assistant_bot.services.backup.retention import (
    RetentionResult,
)

# =========================================================
# STRESS CONFIGURATION
# =========================================================


CONCURRENT_WORKERS = 64

WAIT_TIMEOUT_SECONDS = 10.0


# =========================================================
# TEST DOUBLES
# =========================================================


class ProjectReader:
    """
    Return one fixed project.
    """

    def __init__(
        self,
        project: ProjectSchema,
    ) -> None:
        self._project = project

    def get_project(
        self,
        project_id: str,
    ) -> ProjectSchema:
        if project_id != self._project.id:
            raise AssertionError(f"Unexpected project ID: {project_id}")

        return self._project


class SettingsReader:
    """
    Return one fixed application settings snapshot.
    """

    def __init__(
        self,
        settings: AppSettingsSchema,
    ) -> None:
        self._settings = settings

    def get_settings(
        self,
    ) -> AppSettingsSchema:
        return self._settings


class ThreadSafeHistoryWriter:
    """
    Thread-safe in-memory backup history writer.
    """

    def __init__(
        self,
    ) -> None:
        self._lock = Lock()

        self.records: list[BackupHistoryCreateSchema] = []

    def create(
        self,
        data: BackupHistoryCreateSchema,
    ) -> BackupHistorySchema:
        with self._lock:
            self.records.append(
                data,
            )

            history_id = f"history-{len(self.records)}"

        return BackupHistorySchema(
            id=history_id,
            **data.model_dump(),
        )


class ThreadSafeRetentionRunner:
    """
    Thread-safe retention test double.
    """

    def __init__(
        self,
    ) -> None:
        self._lock = Lock()

        self.calls: list[
            tuple[
                str,
                int,
            ]
        ] = []

    def cleanup(
        self,
        *,
        project_id: str,
        keep_last: int,
    ) -> RetentionResult:
        with self._lock:
            self.calls.append(
                (
                    project_id,
                    keep_last,
                )
            )

        return RetentionResult()


class BlockingBackupRunner:
    """
    Block the winning backup until all competing callers
    have attempted to enter the coordinator.

    Only one call should ever reach backup_project().
    """

    def __init__(
        self,
        result: BackupResult,
    ) -> None:
        self._result = result

        self._lock = Lock()

        self.entered = Event()

        self.release = Event()

        self.call_count = 0

    def backup_project(
        self,
        project: ProjectSchema,
    ) -> BackupResult:
        del project

        with self._lock:
            self.call_count += 1

        self.entered.set()

        if not self.release.wait(
            timeout=WAIT_TIMEOUT_SECONDS,
        ):
            raise RuntimeError("Timed out waiting for stress-test release.")

        return self._result


class RunnerFactory:
    """
    Return the same blocking runner for every request.
    """

    def __init__(
        self,
        runner: BlockingBackupRunner,
    ) -> None:
        self._runner = runner

    def __call__(
        self,
        settings: AppSettingsSchema,
    ) -> BlockingBackupRunner:
        del settings

        return self._runner


# =========================================================
# BUILDERS
# =========================================================


def build_project(
    tmp_path: Path,
) -> ProjectSchema:
    return ProjectSchema(
        id="stress-project",
        name="Stress Project",
        enabled=True,
        database=DatabaseSchema(
            type=DatabaseType.SQLITE,
            path=(tmp_path / "database.sqlite3"),
        ),
        media=MediaSchema(
            enabled=False,
            path=(tmp_path / "media"),
        ),
        schedule=ScheduleSchema(
            enabled=True,
            interval=1,
            unit=ScheduleUnit.HOURS,
        ),
    )


def build_settings(
    tmp_path: Path,
) -> AppSettingsSchema:
    return AppSettingsSchema(
        bot_enabled=True,
        backup_enabled=True,
        backup_directory=(tmp_path / "backups"),
        compression_level=6,
        retention_enabled=True,
        retention_keep_last=10,
    )


def build_result(
    tmp_path: Path,
) -> BackupResult:
    now = datetime.now(
        timezone.utc,
    )

    return BackupResult(
        project_id="stress-project",
        project_name="Stress Project",
        status=BackupStatus.SUCCESS,
        archive_path=(tmp_path / "stress-backup.zip"),
        started_at=now,
        finished_at=now,
        database_size_bytes=1024,
        media_size_bytes=0,
        archive_size_bytes=512,
        media_file_count=0,
        checksum=ChecksumResult(
            algorithm="sha256",
            value="stress-checksum",
        ),
    )


# =========================================================
# STRESS TEST
# =========================================================


def test_many_concurrent_requests_allow_only_one_backup(
    tmp_path: Path,
) -> None:
    """
    Hit one project with many simultaneous backup requests.

    Expected invariant:

    - exactly one request acquires the project lock
    - exactly one request reaches BackupRunner
    - every competing request receives
      BackupAlreadyRunningError
    - exactly one success history is persisted
    - retention executes exactly once
    - the project lock is released after completion
    """

    project = build_project(
        tmp_path,
    )

    settings = build_settings(
        tmp_path,
    )

    history = ThreadSafeHistoryWriter()

    retention = ThreadSafeRetentionRunner()

    runner = BlockingBackupRunner(
        build_result(
            tmp_path,
        )
    )

    coordinator = BackupCoordinator(
        projects=ProjectReader(
            project,
        ),
        settings=SettingsReader(
            settings,
        ),
        history=history,
        retention=retention,
        runner_factory=RunnerFactory(
            runner,
        ),
    )

    # -----------------------------------------------------
    # SYNCHRONIZE ALL WORKERS
    # -----------------------------------------------------

    start_barrier = Barrier(
        CONCURRENT_WORKERS,
    )

    result_lock = Lock()

    rejected_count = 0

    successful_results: list[BackupResult] = []

    unexpected_errors: list[BaseException] = []

    rejected_workers_done = Event()

    # -----------------------------------------------------
    # WORKER
    # -----------------------------------------------------

    def worker() -> None:
        nonlocal rejected_count

        try:
            start_barrier.wait(
                timeout=WAIT_TIMEOUT_SECONDS,
            )

            result = coordinator.run(
                project.id,
            )

        except BackupAlreadyRunningError:
            with result_lock:
                rejected_count += 1

                if rejected_count == CONCURRENT_WORKERS - 1:
                    rejected_workers_done.set()

        except BaseException as exc:
            with result_lock:
                unexpected_errors.append(
                    exc,
                )

        else:
            with result_lock:
                successful_results.append(
                    result,
                )

    # -----------------------------------------------------
    # START STRESS WORKERS
    # -----------------------------------------------------

    threads = [
        Thread(
            target=worker,
            name=f"backup-stress-{index}",
        )
        for index in range(CONCURRENT_WORKERS)
    ]

    for thread in threads:
        thread.start()

    # -----------------------------------------------------
    # ONE WORKER MUST ENTER THE REAL BACKUP
    # -----------------------------------------------------

    assert runner.entered.wait(
        timeout=WAIT_TIMEOUT_SECONDS,
    )

    assert coordinator.is_running(
        project.id,
    )

    # -----------------------------------------------------
    # EVERY OTHER WORKER MUST BE REJECTED WHILE THE
    # WINNING BACKUP IS STILL BLOCKED.
    # -----------------------------------------------------

    assert rejected_workers_done.wait(
        timeout=WAIT_TIMEOUT_SECONDS,
    )

    assert rejected_count == (CONCURRENT_WORKERS - 1)

    assert runner.call_count == 1

    assert unexpected_errors == []

    # -----------------------------------------------------
    # RELEASE THE SINGLE WINNING BACKUP
    # -----------------------------------------------------

    runner.release.set()

    for thread in threads:
        thread.join(
            timeout=WAIT_TIMEOUT_SECONDS,
        )

    # -----------------------------------------------------
    # NO THREAD MAY REMAIN STUCK
    # -----------------------------------------------------

    assert all(not thread.is_alive() for thread in threads)

    # -----------------------------------------------------
    # FINAL INVARIANTS
    # -----------------------------------------------------

    assert runner.call_count == 1

    assert rejected_count == (CONCURRENT_WORKERS - 1)

    assert len(successful_results) == 1

    assert unexpected_errors == []

    assert len(history.records) == 1

    assert history.records[0].status is BackupStatus.SUCCESS

    assert history.records[0].project_id == project.id

    assert retention.calls == [
        (
            project.id,
            settings.retention_keep_last,
        )
    ]

    assert not coordinator.is_running(
        project.id,
    )


def test_project_lock_remains_reusable_after_concurrency_stress(
    tmp_path: Path,
) -> None:
    """
    Verify the coordinator is still usable after a
    concurrent rejection storm.

    This catches leaked/stuck project-lock state.
    """

    project = build_project(
        tmp_path,
    )

    settings = build_settings(
        tmp_path,
    )

    history = ThreadSafeHistoryWriter()

    retention = ThreadSafeRetentionRunner()

    runner = BlockingBackupRunner(
        build_result(
            tmp_path,
        )
    )

    coordinator = BackupCoordinator(
        projects=ProjectReader(
            project,
        ),
        settings=SettingsReader(
            settings,
        ),
        history=history,
        retention=retention,
        runner_factory=RunnerFactory(
            runner,
        ),
    )

    first_errors: list[BaseException] = []

    # -----------------------------------------------------
    # FIRST BACKUP
    # -----------------------------------------------------

    def first_backup() -> None:
        try:
            coordinator.run(
                project.id,
            )

        except BaseException as exc:
            first_errors.append(
                exc,
            )

    thread = Thread(
        target=first_backup,
    )

    thread.start()

    assert runner.entered.wait(
        timeout=WAIT_TIMEOUT_SECONDS,
    )

    # -----------------------------------------------------
    # REJECTION STORM
    # -----------------------------------------------------

    for _ in range(
        100,
    ):
        try:
            coordinator.run(
                project.id,
            )

        except BackupAlreadyRunningError:
            continue

        raise AssertionError(
            ("Concurrent backup unexpectedly " "acquired the project lock.")
        )

    # -----------------------------------------------------
    # FINISH FIRST BACKUP
    # -----------------------------------------------------

    runner.release.set()

    thread.join(
        timeout=WAIT_TIMEOUT_SECONDS,
    )

    assert not thread.is_alive()

    assert first_errors == []

    assert not coordinator.is_running(
        project.id,
    )

    # -----------------------------------------------------
    # RESET BLOCKING EVENTS FOR A SECOND VALID BACKUP
    # -----------------------------------------------------

    runner.entered.clear()

    runner.release.clear()

    second_errors: list[BaseException] = []

    def second_backup() -> None:
        try:
            coordinator.run(
                project.id,
            )

        except BaseException as exc:
            second_errors.append(
                exc,
            )

    second_thread = Thread(
        target=second_backup,
    )

    second_thread.start()

    assert runner.entered.wait(
        timeout=WAIT_TIMEOUT_SECONDS,
    )

    assert coordinator.is_running(
        project.id,
    )

    runner.release.set()

    second_thread.join(
        timeout=WAIT_TIMEOUT_SECONDS,
    )

    assert not second_thread.is_alive()

    assert second_errors == []

    # -----------------------------------------------------
    # TWO GENUINE BACKUPS MUST HAVE COMPLETED.
    # -----------------------------------------------------

    assert runner.call_count == 2

    assert len(history.records) == 2

    assert len(retention.calls) == 2

    assert not coordinator.is_running(
        project.id,
    )
