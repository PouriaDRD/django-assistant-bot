from __future__ import annotations

from datetime import (
    datetime,
    timezone,
)
from pathlib import Path
from threading import (
    Event,
    Thread,
)

import pytest

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
    BackupDisabledError,
    BackupExecutionError,
    BackupHistoryError,
    BotDisabledError,
    ProjectBackupDisabledError,
)
from django_assistant_bot.services.backup.models import (
    BackupResult,
    ChecksumResult,
)
from django_assistant_bot.services.backup.retention import (
    RetentionResult,
)

# =========================================================
# TEST DOUBLES
# =========================================================


class FakeProjectReader:
    def __init__(
        self,
        project: ProjectSchema,
    ) -> None:
        self.project = project

        self.requested_ids: list[str] = []

    def get_project(
        self,
        project_id: str,
    ) -> ProjectSchema:
        self.requested_ids.append(
            project_id,
        )

        return self.project


class FakeSettingsReader:
    def __init__(
        self,
        settings: AppSettingsSchema,
    ) -> None:
        self.settings = settings

        self.call_count = 0

    def get_settings(
        self,
    ) -> AppSettingsSchema:
        self.call_count += 1

        return self.settings


class FakeHistoryWriter:
    def __init__(
        self,
        *,
        fail: bool = False,
    ) -> None:
        self.fail = fail

        self.records: list[BackupHistoryCreateSchema] = []

    def create(
        self,
        data: BackupHistoryCreateSchema,
    ) -> BackupHistorySchema:
        if self.fail:
            raise RuntimeError("history unavailable")

        self.records.append(
            data,
        )

        return BackupHistorySchema(
            id=(f"history-" f"{len(self.records)}"),
            **data.model_dump(),
        )


class FakeBackupRunner:
    def __init__(
        self,
        *,
        result: BackupResult | None = None,
        error: Exception | None = None,
    ) -> None:
        self.result = result

        self.error = error

        self.projects: list[ProjectSchema] = []

    def backup_project(
        self,
        project: ProjectSchema,
    ) -> BackupResult:
        self.projects.append(
            project,
        )

        if self.error is not None:
            raise self.error

        if self.result is None:
            raise AssertionError("Fake backup result is missing.")

        return self.result


class BlockingBackupRunner:
    def __init__(
        self,
        result: BackupResult,
    ) -> None:
        self.result = result

        self.entered = Event()

        self.release = Event()

    def backup_project(
        self,
        project: ProjectSchema,
    ) -> BackupResult:
        del project

        self.entered.set()

        if not self.release.wait(
            timeout=5,
        ):
            raise RuntimeError(("Timed out waiting " "for test release."))

        return self.result


class FakeRunnerFactory:
    def __init__(
        self,
        runner: FakeBackupRunner | BlockingBackupRunner,
    ) -> None:
        self.runner = runner

        self.settings: list[AppSettingsSchema] = []

    def __call__(
        self,
        settings: AppSettingsSchema,
    ) -> FakeBackupRunner | BlockingBackupRunner:
        self.settings.append(
            settings,
        )

        return self.runner


class FakeRetentionRunner:
    def __init__(
        self,
        *,
        error: Exception | None = None,
        result: RetentionResult | None = None,
    ) -> None:
        self.error = error

        self.result = result if result is not None else RetentionResult()

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
        self.calls.append(
            (
                project_id,
                keep_last,
            )
        )

        if self.error is not None:
            raise self.error

        return self.result


# =========================================================
# BUILDERS
# =========================================================


def build_project(
    tmp_path: Path,
    *,
    project_id: str = "project-1",
) -> ProjectSchema:
    return ProjectSchema(
        id=project_id,
        name="Test Project",
        enabled=True,
        database=DatabaseSchema(
            type=DatabaseType.SQLITE,
            path=(tmp_path / "db.sqlite3"),
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
    *,
    bot_enabled: bool = True,
    backup_enabled: bool = True,
    retention_enabled: bool = True,
    retention_keep_last: int = 5,
) -> AppSettingsSchema:
    return AppSettingsSchema(
        bot_enabled=bot_enabled,
        backup_enabled=backup_enabled,
        backup_directory=(tmp_path / "backups"),
        compression_level=7,
        retention_enabled=(retention_enabled),
        retention_keep_last=(retention_keep_last),
    )


def build_result(
    tmp_path: Path,
    *,
    project_id: str = "project-1",
) -> BackupResult:
    started_at = datetime.now(
        timezone.utc,
    )

    finished_at = datetime.now(
        timezone.utc,
    )

    return BackupResult(
        project_id=project_id,
        project_name="Test Project",
        status=BackupStatus.SUCCESS,
        archive_path=(tmp_path / "backup.zip"),
        started_at=started_at,
        finished_at=finished_at,
        database_size_bytes=100,
        media_size_bytes=200,
        archive_size_bytes=250,
        media_file_count=3,
        checksum=ChecksumResult(
            algorithm="sha256",
            value="test-checksum",
        ),
    )


def build_coordinator(
    *,
    project: ProjectSchema,
    settings: AppSettingsSchema,
    runner: FakeBackupRunner | BlockingBackupRunner,
    history: FakeHistoryWriter | None = None,
    retention: FakeRetentionRunner | None = None,
) -> tuple[
    BackupCoordinator,
    FakeHistoryWriter,
    FakeRunnerFactory,
    FakeRetentionRunner,
]:
    project_reader = FakeProjectReader(
        project,
    )

    settings_reader = FakeSettingsReader(
        settings,
    )

    history_writer = history if history is not None else FakeHistoryWriter()

    retention_runner = retention if retention is not None else FakeRetentionRunner()

    factory = FakeRunnerFactory(
        runner,
    )

    coordinator = BackupCoordinator(
        projects=project_reader,
        settings=settings_reader,
        history=history_writer,
        retention=retention_runner,
        runner_factory=factory,
    )

    return (
        coordinator,
        history_writer,
        factory,
        retention_runner,
    )


# =========================================================
# SUCCESS
# =========================================================


def test_successful_backup_records_history(
    tmp_path: Path,
) -> None:
    project = build_project(
        tmp_path,
    )

    settings = build_settings(
        tmp_path,
    )

    result = build_result(
        tmp_path,
    )

    runner = FakeBackupRunner(
        result=result,
    )

    (
        coordinator,
        history,
        factory,
        retention,
    ) = build_coordinator(
        project=project,
        settings=settings,
        runner=runner,
    )

    returned = coordinator.run(
        project.id,
    )

    assert returned is result

    assert runner.projects == [
        project,
    ]

    assert factory.settings == [
        settings,
    ]

    assert len(history.records) == 1

    record = history.records[0]

    assert record.status is BackupStatus.SUCCESS

    assert record.project_id == project.id

    assert record.archive_path == result.archive_path

    assert record.database_size_bytes == 100

    assert record.media_size_bytes == 200

    assert record.archive_size_bytes == 250

    assert record.media_file_count == 3

    assert record.checksum_algorithm == "sha256"

    assert record.checksum_value == "test-checksum"

    assert record.error_message is None

    assert retention.calls == [
        (
            project.id,
            settings.retention_keep_last,
        )
    ]


# =========================================================
# GLOBAL BOT DISABLE
# =========================================================


def test_bot_disabled_prevents_execution(
    tmp_path: Path,
) -> None:
    project = build_project(
        tmp_path,
    )

    settings = build_settings(
        tmp_path,
        bot_enabled=False,
    )

    runner = FakeBackupRunner(
        result=build_result(
            tmp_path,
        ),
    )

    (
        coordinator,
        history,
        factory,
        retention,
    ) = build_coordinator(
        project=project,
        settings=settings,
        runner=runner,
    )

    with pytest.raises(
        BotDisabledError,
        match="disabled",
    ):
        coordinator.run(
            project.id,
        )

    assert runner.projects == []

    assert factory.settings == []

    assert history.records == []

    assert retention.calls == []

    assert not coordinator.is_running(
        project.id,
    )


# =========================================================
# GLOBAL BACKUP DISABLE
# =========================================================


def test_backup_disabled_prevents_execution(
    tmp_path: Path,
) -> None:
    project = build_project(
        tmp_path,
    )

    settings = build_settings(
        tmp_path,
        backup_enabled=False,
    )

    runner = FakeBackupRunner(
        result=build_result(
            tmp_path,
        ),
    )

    (
        coordinator,
        history,
        factory,
        retention,
    ) = build_coordinator(
        project=project,
        settings=settings,
        runner=runner,
    )

    with pytest.raises(
        BackupDisabledError,
        match="disabled",
    ):
        coordinator.run(
            project.id,
        )

    assert runner.projects == []

    assert factory.settings == []

    assert history.records == []

    assert retention.calls == []

    assert not coordinator.is_running(
        project.id,
    )


# =========================================================
# FAILURE HISTORY
# =========================================================


def test_failed_backup_records_failed_history(
    tmp_path: Path,
) -> None:
    project = build_project(
        tmp_path,
    )

    settings = build_settings(
        tmp_path,
    )

    runner = FakeBackupRunner(
        error=RuntimeError("disk failure"),
    )

    (
        coordinator,
        history,
        _,
        retention,
    ) = build_coordinator(
        project=project,
        settings=settings,
        runner=runner,
    )

    with pytest.raises(
        BackupExecutionError,
        match="Backup failed",
    ):
        coordinator.run(
            project.id,
        )

    assert len(history.records) == 1

    record = history.records[0]

    assert record.status is BackupStatus.FAILED

    assert record.project_id == project.id

    assert record.error_message == "disk failure"

    assert record.archive_path is None

    assert record.database_size_bytes == 0

    assert record.media_size_bytes == 0

    assert record.archive_size_bytes == 0

    assert record.media_file_count == 0

    assert record.finished_at is not None

    assert retention.calls == []


# =========================================================
# LOCK RELEASE
# =========================================================


def test_lock_is_released_after_failure(
    tmp_path: Path,
) -> None:
    project = build_project(
        tmp_path,
    )

    settings = build_settings(
        tmp_path,
    )

    runner = FakeBackupRunner(
        error=RuntimeError("first failure"),
    )

    (
        coordinator,
        _,
        _,
        retention,
    ) = build_coordinator(
        project=project,
        settings=settings,
        runner=runner,
    )

    with pytest.raises(
        BackupExecutionError,
    ):
        coordinator.run(
            project.id,
        )

    assert not coordinator.is_running(
        project.id,
    )

    assert retention.calls == []

    runner.error = None

    runner.result = build_result(
        tmp_path,
    )

    result = coordinator.run(
        project.id,
    )

    assert result.status is BackupStatus.SUCCESS

    assert retention.calls == [
        (
            project.id,
            settings.retention_keep_last,
        )
    ]


# =========================================================
# CONCURRENCY
# =========================================================


def test_same_project_cannot_run_concurrently(
    tmp_path: Path,
) -> None:
    project = build_project(
        tmp_path,
    )

    settings = build_settings(
        tmp_path,
    )

    runner = BlockingBackupRunner(
        build_result(
            tmp_path,
        ),
    )

    (
        coordinator,
        history,
        _,
        retention,
    ) = build_coordinator(
        project=project,
        settings=settings,
        runner=runner,
    )

    worker_errors: list[BaseException] = []

    def run_backup() -> None:
        try:
            coordinator.run(
                project.id,
            )

        except BaseException as exc:
            worker_errors.append(
                exc,
            )

    thread = Thread(
        target=run_backup,
    )

    thread.start()

    assert runner.entered.wait(
        timeout=5,
    )

    assert coordinator.is_running(
        project.id,
    )

    with pytest.raises(
        BackupAlreadyRunningError,
        match="already running",
    ):
        coordinator.run(
            project.id,
        )

    runner.release.set()

    thread.join(
        timeout=5,
    )

    assert not thread.is_alive()

    assert worker_errors == []

    assert len(history.records) == 1

    assert retention.calls == [
        (
            project.id,
            settings.retention_keep_last,
        )
    ]

    assert not coordinator.is_running(
        project.id,
    )


# =========================================================
# HISTORY FAILURE
# =========================================================


def test_successful_backup_with_history_failure_raises_error(
    tmp_path: Path,
) -> None:
    project = build_project(
        tmp_path,
    )

    settings = build_settings(
        tmp_path,
    )

    runner = FakeBackupRunner(
        result=build_result(
            tmp_path,
        ),
    )

    history = FakeHistoryWriter(
        fail=True,
    )

    retention = FakeRetentionRunner()

    (
        coordinator,
        _,
        _,
        _,
    ) = build_coordinator(
        project=project,
        settings=settings,
        runner=runner,
        history=history,
        retention=retention,
    )

    with pytest.raises(
        BackupHistoryError,
        match="history",
    ):
        coordinator.run(
            project.id,
        )

    assert retention.calls == []

    assert not coordinator.is_running(
        project.id,
    )


# =========================================================
# INPUT
# =========================================================


def test_empty_project_id_is_rejected(
    tmp_path: Path,
) -> None:
    project = build_project(
        tmp_path,
    )

    runner = FakeBackupRunner(
        result=build_result(
            tmp_path,
        ),
    )

    (
        coordinator,
        history,
        _,
        retention,
    ) = build_coordinator(
        project=project,
        settings=build_settings(
            tmp_path,
        ),
        runner=runner,
    )

    with pytest.raises(
        ValueError,
        match="cannot be empty",
    ):
        coordinator.run(
            "   ",
        )

    assert runner.projects == []

    assert history.records == []

    assert retention.calls == []


def test_disabled_project_is_rejected_explicitly(
    tmp_path: Path,
) -> None:
    project = build_project(
        tmp_path,
    )

    project = project.model_copy(
        update={
            "enabled": False,
        }
    )

    runner = FakeBackupRunner(
        result=build_result(
            tmp_path,
        ),
    )

    (
        coordinator,
        history,
        factory,
        retention,
    ) = build_coordinator(
        project=project,
        settings=build_settings(
            tmp_path,
        ),
        runner=runner,
    )

    with pytest.raises(
        ProjectBackupDisabledError,
        match="disabled",
    ):
        coordinator.run(
            project.id,
        )

    assert runner.projects == []

    assert factory.settings == []

    assert history.records == []

    assert retention.calls == []

    assert not coordinator.is_running(
        project.id,
    )


# =========================================================
# RETENTION
# =========================================================


def test_successful_backup_runs_retention(
    tmp_path: Path,
) -> None:
    project = build_project(
        tmp_path,
    )

    settings = build_settings(
        tmp_path,
        retention_enabled=True,
        retention_keep_last=7,
    )

    backup_result = build_result(
        tmp_path,
    )

    runner = FakeBackupRunner(
        result=backup_result,
    )

    retention = FakeRetentionRunner()

    (
        coordinator,
        history,
        _,
        returned_retention,
    ) = build_coordinator(
        project=project,
        settings=settings,
        runner=runner,
        retention=retention,
    )

    returned = coordinator.run(
        project.id,
    )

    assert returned is backup_result

    assert len(history.records) == 1

    assert history.records[0].status is BackupStatus.SUCCESS

    assert returned_retention is retention

    assert retention.calls == [
        (
            project.id,
            7,
        )
    ]


def test_disabled_retention_is_not_executed(
    tmp_path: Path,
) -> None:
    project = build_project(
        tmp_path,
    )

    settings = build_settings(
        tmp_path,
        retention_enabled=False,
    )

    backup_result = build_result(
        tmp_path,
    )

    runner = FakeBackupRunner(
        result=backup_result,
    )

    retention = FakeRetentionRunner()

    (
        coordinator,
        history,
        _,
        _,
    ) = build_coordinator(
        project=project,
        settings=settings,
        runner=runner,
        retention=retention,
    )

    returned = coordinator.run(
        project.id,
    )

    assert returned is backup_result

    assert len(history.records) == 1

    assert history.records[0].status is BackupStatus.SUCCESS

    assert retention.calls == []


def test_retention_failure_does_not_fail_successful_backup(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    project = build_project(
        tmp_path,
    )

    settings = build_settings(
        tmp_path,
        retention_enabled=True,
        retention_keep_last=5,
    )

    backup_result = build_result(
        tmp_path,
    )

    runner = FakeBackupRunner(
        result=backup_result,
    )

    retention = FakeRetentionRunner(
        error=RuntimeError("retention failed"),
    )

    (
        coordinator,
        history,
        _,
        _,
    ) = build_coordinator(
        project=project,
        settings=settings,
        runner=runner,
        retention=retention,
    )

    returned = coordinator.run(
        project.id,
    )

    assert returned is backup_result

    assert len(history.records) == 1

    assert history.records[0].status is BackupStatus.SUCCESS

    assert retention.calls == [
        (
            project.id,
            settings.retention_keep_last,
        )
    ]

    assert "Backup retention cleanup failed" in caplog.text

    assert not coordinator.is_running(
        project.id,
    )


def test_history_failure_prevents_retention(
    tmp_path: Path,
) -> None:
    project = build_project(
        tmp_path,
    )

    settings = build_settings(
        tmp_path,
    )

    backup_result = build_result(
        tmp_path,
    )

    runner = FakeBackupRunner(
        result=backup_result,
    )

    history = FakeHistoryWriter(
        fail=True,
    )

    retention = FakeRetentionRunner()

    (
        coordinator,
        _,
        _,
        _,
    ) = build_coordinator(
        project=project,
        settings=settings,
        runner=runner,
        history=history,
        retention=retention,
    )

    with pytest.raises(
        BackupHistoryError,
        match="history",
    ):
        coordinator.run(
            project.id,
        )

    assert retention.calls == []

    assert not coordinator.is_running(
        project.id,
    )
