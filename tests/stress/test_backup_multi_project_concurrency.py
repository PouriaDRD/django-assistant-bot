from __future__ import annotations
from collections.abc import (
    Callable,
)
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


PROJECT_COUNT = 16

WAIT_TIMEOUT_SECONDS = 10.0


# =========================================================
# TEST DOUBLES
# =========================================================


class MultiProjectReader:
    """
    Return projects by ID.
    """

    def __init__(
        self,
        projects: list[ProjectSchema],
    ) -> None:
        self._projects = {project.id: project for project in projects}

    def get_project(
        self,
        project_id: str,
    ) -> ProjectSchema:
        project = self._projects.get(
            project_id,
        )

        if project is None:
            raise AssertionError(f"Unexpected project ID: {project_id}")

        return project


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
    Thread-safe in-memory history writer.
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
    Thread-safe retention runner.
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


class MultiProjectBlockingRunner:
    """
    Allow different projects to enter concurrently,
    then block all of them until released.

    This lets the test verify that the coordinator's
    project lock is scoped per project instead of globally
    blocking all backup execution.
    """

    def __init__(
        self,
        expected_projects: int,
        result_builder: ResultBuilder,
    ) -> None:
        self._expected_projects = expected_projects

        self._result_builder = result_builder

        self._lock = Lock()

        self._all_entered = Event()

        self._release = Event()

        self.entered_project_ids: set[str] = set()

        self.call_count = 0

    def backup_project(
        self,
        project: ProjectSchema,
    ) -> BackupResult:
        with self._lock:
            self.call_count += 1

            self.entered_project_ids.add(
                project.id,
            )

            if len(self.entered_project_ids) == self._expected_projects:
                self._all_entered.set()

        if not self._release.wait(
            timeout=WAIT_TIMEOUT_SECONDS,
        ):
            raise RuntimeError(
                ("Timed out waiting for " "multi-project stress release.")
            )

        return self._result_builder(
            project,
        )

    @property
    def all_entered(
        self,
    ) -> Event:
        return self._all_entered

    @property
    def release(
        self,
    ) -> Event:
        return self._release


class RunnerFactory:
    """
    Return one shared multi-project runner.
    """

    def __init__(
        self,
        runner: MultiProjectBlockingRunner,
    ) -> None:
        self._runner = runner

    def __call__(
        self,
        settings: AppSettingsSchema,
    ) -> MultiProjectBlockingRunner:
        del settings

        return self._runner


# =========================================================
# TYPE ALIAS
# =========================================================


type ResultBuilder = (Callable[[ProjectSchema], BackupResult])


# =========================================================
# BUILDERS
# =========================================================


def build_project(
    tmp_path: Path,
    *,
    index: int,
) -> ProjectSchema:
    project_id = f"stress-project-{index}"

    return ProjectSchema(
        id=project_id,
        name=(f"Stress Project {index}"),
        enabled=True,
        database=DatabaseSchema(
            type=DatabaseType.SQLITE,
            path=(tmp_path / f"{project_id}.sqlite3"),
        ),
        media=MediaSchema(
            enabled=False,
            path=(tmp_path / f"media-{index}"),
        ),
        schedule=ScheduleSchema(
            enabled=True,
            interval=1,
            unit=ScheduleUnit.HOURS,
        ),
    )


def build_projects(
    tmp_path: Path,
) -> list[ProjectSchema]:
    return [
        build_project(
            tmp_path,
            index=index,
        )
        for index in range(PROJECT_COUNT)
    ]


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
    project: ProjectSchema,
) -> BackupResult:
    now = datetime.now(
        timezone.utc,
    )

    return BackupResult(
        project_id=project.id,
        project_name=project.name,
        status=BackupStatus.SUCCESS,
        archive_path=(tmp_path / f"{project.id}.zip"),
        started_at=now,
        finished_at=now,
        database_size_bytes=1024,
        media_size_bytes=0,
        archive_size_bytes=512,
        media_file_count=0,
        checksum=ChecksumResult(
            algorithm="sha256",
            value=(f"checksum-{project.id}"),
        ),
    )


# =========================================================
# STRESS TEST
# =========================================================


def test_different_projects_can_run_concurrently(
    tmp_path: Path,
) -> None:
    """
    Start many different projects at the same time.

    Expected invariant:

    - every unique project acquires its own logical lock
    - all projects may reach BackupRunner concurrently
    - no project blocks a different project
    - each project creates exactly one history record
    - retention runs exactly once per project
    - all project locks are released afterwards
    """

    projects = build_projects(
        tmp_path,
    )

    settings = build_settings(
        tmp_path,
    )

    history = ThreadSafeHistoryWriter()

    retention = ThreadSafeRetentionRunner()

    runner = MultiProjectBlockingRunner(
        expected_projects=PROJECT_COUNT,
        result_builder=(
            lambda project: (
                build_result(
                    tmp_path,
                    project,
                )
            )
        ),
    )

    coordinator = BackupCoordinator(
        projects=MultiProjectReader(
            projects,
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
    # START ALL PROJECTS TOGETHER
    # -----------------------------------------------------

    start_barrier = Barrier(
        PROJECT_COUNT,
    )

    result_lock = Lock()

    successful_results: list[BackupResult] = []

    unexpected_errors: list[BaseException] = []

    def worker(
        project: ProjectSchema,
    ) -> None:
        try:
            start_barrier.wait(
                timeout=WAIT_TIMEOUT_SECONDS,
            )

            result = coordinator.run(
                project.id,
            )

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

    threads = [
        Thread(
            target=worker,
            args=(project,),
            name=(f"multi-project-stress-{project.id}"),
        )
        for project in projects
    ]

    for thread in threads:
        thread.start()

    # -----------------------------------------------------
    # ALL PROJECTS MUST ENTER BACKUP RUNNER BEFORE RELEASE
    # -----------------------------------------------------

    assert runner.all_entered.wait(
        timeout=WAIT_TIMEOUT_SECONDS,
    )

    assert runner.call_count == (PROJECT_COUNT)

    assert runner.entered_project_ids == {project.id for project in projects}

    # Every project should currently be marked as running.
    for project in projects:
        assert coordinator.is_running(
            project.id,
        )

    assert unexpected_errors == []

    # -----------------------------------------------------
    # RELEASE ALL RUNNING BACKUPS
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

    assert unexpected_errors == []

    # -----------------------------------------------------
    # EVERY PROJECT MUST COMPLETE ONCE
    # -----------------------------------------------------

    assert len(successful_results) == PROJECT_COUNT

    successful_project_ids = {result.project_id for result in successful_results}

    assert successful_project_ids == {project.id for project in projects}

    assert runner.call_count == (PROJECT_COUNT)

    # -----------------------------------------------------
    # HISTORY
    # -----------------------------------------------------

    assert len(history.records) == PROJECT_COUNT

    history_project_ids = {record.project_id for record in history.records}

    assert history_project_ids == {project.id for project in projects}

    assert all(record.status is BackupStatus.SUCCESS for record in history.records)

    # -----------------------------------------------------
    # RETENTION
    # -----------------------------------------------------

    assert len(retention.calls) == PROJECT_COUNT

    retention_project_ids = {project_id for project_id, _ in retention.calls}

    assert retention_project_ids == {project.id for project in projects}

    assert all(
        keep_last == settings.retention_keep_last for _, keep_last in retention.calls
    )

    # -----------------------------------------------------
    # LOCK CLEANUP
    # -----------------------------------------------------

    for project in projects:
        assert not coordinator.is_running(
            project.id,
        )
