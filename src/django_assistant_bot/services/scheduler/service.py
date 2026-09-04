from __future__ import annotations

import asyncio
import logging
from typing import Protocol

from apscheduler.jobstores.base import (
    JobLookupError,
)
from apscheduler.schedulers.asyncio import (
    AsyncIOScheduler,
)
from apscheduler.triggers.interval import (
    IntervalTrigger,
)

from django_assistant_bot.database.models.enums import (
    ScheduleUnit,
)
from django_assistant_bot.schemas.project import (
    ProjectSchema,
)
from django_assistant_bot.services.backup import (
    BackupAlreadyRunningError,
    BackupDisabledError,
    BackupExecutionError,
    BackupHistoryError,
    BackupResult,
    ProjectBackupDisabledError,
)

logger = logging.getLogger(
    __name__,
)


JOB_PREFIX = "project-backup:"


class ProjectReader(Protocol):
    """
    Minimal project service contract required by scheduler.
    """

    def list_projects(
        self,
    ) -> list[ProjectSchema]: ...

    def get_project(
        self,
        project_id: str,
    ) -> ProjectSchema: ...


class BackupRunner(Protocol):
    """
    Backup coordinator contract required by scheduler.
    """

    def run(
        self,
        project_id: str,
    ) -> BackupResult: ...


class BackupDelivery(Protocol):
    async def deliver(
        self,
        result: BackupResult,
    ) -> object: ...


class BackupSchedulerService:
    """
    Manage automatic backup jobs.

    Responsibilities:
    - restore scheduled jobs at application startup
    - create/update project jobs
    - remove disabled project jobs
    - execute backups through BackupCoordinator
    - prevent scheduler concerns from leaking into handlers
    """

    def __init__(
        self,
        *,
        projects: ProjectReader,
        backups: BackupRunner,
        scheduler: AsyncIOScheduler | None = None,
    ) -> None:
        self._projects = projects
        self._backups = backups
        self._delivery: BackupDelivery | None = None
        self._scheduler = scheduler if scheduler is not None else AsyncIOScheduler()

        self._started = False

    # =====================================================
    # LIFECYCLE
    # =====================================================

    def start(self) -> None:
        """
        Start APScheduler and restore project jobs.
        """

        if self._started:
            return

        self._scheduler.start()

        self._started = True

        self.sync_all()

        logger.info("Backup scheduler started.")

    def stop(
        self,
        *,
        wait: bool = False,
    ) -> None:
        """
        Stop APScheduler.

        Safe to call more than once.
        """

        if not self._started:
            return

        self._scheduler.shutdown(
            wait=wait,
        )

        self._started = False

        logger.info("Backup scheduler stopped.")

    # =====================================================
    # SYNCHRONIZATION
    # =====================================================

    def sync_all(self) -> None:
        """
        Synchronize all project schedules.

        This is used during startup so jobs are restored
        from persisted project configuration.
        """

        projects = self._projects.list_projects()

        active_project_ids: set[str] = set()

        for project in projects:
            if self._should_schedule(project):
                active_project_ids.add(project.id)

            self.sync_project(project)

        # Remove stale jobs whose projects no longer exist
        # or no longer have scheduling enabled.
        for job in list(self._scheduler.get_jobs()):
            if not job.id.startswith(JOB_PREFIX):
                continue

            project_id = job.id.removeprefix(JOB_PREFIX)

            if project_id not in active_project_ids:
                self.remove_project(project_id)

    def sync_project(
        self,
        project: ProjectSchema,
    ) -> None:
        """
        Create, update or remove one project's job.
        """

        if not self._should_schedule(project):
            self.remove_project(project.id)

            return

        trigger = self._build_trigger(project)

        self._scheduler.add_job(
            self._run_project_backup,
            trigger=trigger,
            id=self._job_id(project.id),
            args=[
                project.id,
            ],
            replace_existing=True,
            coalesce=True,
            max_instances=1,
            misfire_grace_time=300,
        )

        logger.info(
            "Scheduled backup for project %s every %s %s.",
            project.id,
            project.schedule.interval,
            project.schedule.unit.value,
        )

    def remove_project(
        self,
        project_id: str,
    ) -> None:
        """
        Remove a project's scheduled backup job.

        Missing jobs are treated as already removed.
        """

        job_id = self._job_id(project_id)

        try:
            self._scheduler.remove_job(job_id)

        except JobLookupError:
            return

        logger.info(
            "Removed scheduled backup job for project %s.",
            project_id,
        )

    # =====================================================
    # JOB EXECUTION
    # =====================================================

    async def _run_project_backup(
        self,
        project_id: str,
    ) -> None:
        """
        Execute scheduled backup without blocking event loop.
        """

        logger.info(
            "Starting scheduled backup for project %s.",
            project_id,
        )

        try:
            result = await asyncio.to_thread(
                self._backups.run,
                project_id,
            )

        except ProjectBackupDisabledError:
            logger.info(
                "Scheduled backup skipped because project %s " "is disabled.",
                project_id,
            )

        except BackupDisabledError:
            logger.info(
                "Scheduled backup skipped because global " "backups are disabled."
            )

        except BackupAlreadyRunningError:
            logger.info(
                "Scheduled backup skipped because project %s "
                "already has a running backup.",
                project_id,
            )

        except BackupHistoryError:
            logger.exception(
                "Scheduled backup for project %s completed "
                "but history persistence failed.",
                project_id,
            )

        except BackupExecutionError:
            logger.exception(
                "Scheduled backup failed for project %s.",
                project_id,
            )

        except Exception:
            logger.exception(
                "Unexpected scheduled backup failure for " "project %s.",
                project_id,
            )

        else:
            if self._delivery is not None:
                try:
                    await self._delivery.deliver(result)

                except Exception:
                    logger.exception(
                        "Scheduled backup for project %s succeeded "
                        "but delivery failed.",
                        project_id,
                    )
            logger.info(
                "Scheduled backup completed for project %s.",
                project_id,
            )

    def set_delivery(
        self,
        delivery: BackupDelivery,
    ) -> None:
        """
        Attach runtime backup delivery backend.

        Delivery depends on Telegram Bot instance, which is
        created after application bootstrap.
        """

        self._delivery = delivery

    # =====================================================
    # HELPERS
    # =====================================================

    @staticmethod
    def _should_schedule(
        project: ProjectSchema,
    ) -> bool:
        return project.enabled and project.schedule.enabled

    @staticmethod
    def _job_id(
        project_id: str,
    ) -> str:
        return f"{JOB_PREFIX}" f"{project_id}"

    @staticmethod
    def _build_trigger(
        project: ProjectSchema,
    ) -> IntervalTrigger:
        """
        Convert project schedule configuration into
        APScheduler IntervalTrigger.
        """

        interval = project.schedule.interval

        unit = project.schedule.unit

        if unit is ScheduleUnit.MINUTES:
            return IntervalTrigger(
                minutes=interval,
            )

        if unit is ScheduleUnit.HOURS:
            return IntervalTrigger(
                hours=interval,
            )

        if unit is ScheduleUnit.DAYS:
            return IntervalTrigger(
                days=interval,
            )

        raise ValueError(f"Unsupported schedule unit: {unit}")


__all__ = [
    "BackupSchedulerService",
    "JOB_PREFIX",
]
