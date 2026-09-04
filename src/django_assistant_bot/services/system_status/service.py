from __future__ import annotations

import platform
from pathlib import Path
from typing import Protocol

import psutil

from django_assistant_bot.schemas.admin import (
    AdminSchema,
)
from django_assistant_bot.schemas.app_settings import (
    AppSettingsSchema,
)
from django_assistant_bot.schemas.project import (
    ProjectSchema,
)
from django_assistant_bot.schemas.system_status import (
    SchedulerRuntimeStatus,
    SystemStatusSchema,
)

# =========================================================
# DEPENDENCY CONTRACTS
# =========================================================


class SettingsReader(Protocol):
    """
    Minimal settings contract required by system status.
    """

    def get_settings(
        self,
    ) -> AppSettingsSchema: ...


class ProjectReader(Protocol):
    """
    Minimal project contract required by system status.
    """

    def list_projects(
        self,
    ) -> list[ProjectSchema]: ...


class AdminReader(Protocol):
    """
    Minimal administrator contract required by system status.
    """

    def list_admins(
        self,
    ) -> list[AdminSchema]: ...


class SchedulerReader(Protocol):
    """
    Minimal scheduler runtime contract required by system
    status.
    """

    @property
    def is_started(
        self,
    ) -> bool: ...

    @property
    def is_paused(
        self,
    ) -> bool: ...


# =========================================================
# SERVICE
# =========================================================


class SystemStatusService:
    """
    Build an application-wide runtime status snapshot.

    The service exposes application state together with host
    operating-system and resource information.

    It remains independent from Telegram.
    """

    def __init__(
        self,
        *,
        settings: SettingsReader,
        projects: ProjectReader,
        admins: AdminReader,
        scheduler: SchedulerReader,
    ) -> None:
        self._settings = settings

        self._projects = projects

        self._admins = admins

        self._scheduler = scheduler

    def get_status(
        self,
    ) -> SystemStatusSchema:
        """
        Return the current application and host runtime status.
        """

        settings = self._settings.get_settings()

        projects = self._projects.list_projects()

        admins = self._admins.list_admins()

        enabled_project_count = sum(1 for project in projects if project.enabled)

        scheduled_project_count = sum(
            1 for project in projects if (project.enabled and project.schedule.enabled)
        )

        memory = psutil.virtual_memory()

        disk = psutil.disk_usage(self._get_disk_root())

        cpu_physical_cores = psutil.cpu_count(
            logical=False,
        )

        cpu_logical_cores = (
            psutil.cpu_count(
                logical=True,
            )
            or 1
        )

        return SystemStatusSchema(
            # ---------------------------------------------
            # APPLICATION
            # ---------------------------------------------
            bot_enabled=(settings.bot_enabled),
            backup_enabled=(settings.backup_enabled),
            proxy_enabled=(settings.proxy_enabled),
            retention_enabled=(settings.retention_enabled),
            scheduler_status=(self._get_scheduler_status()),
            # ---------------------------------------------
            # PROJECTS
            # ---------------------------------------------
            project_count=len(projects),
            enabled_project_count=(enabled_project_count),
            scheduled_project_count=(scheduled_project_count),
            admin_count=len(admins),
            # ---------------------------------------------
            # RUNTIME
            # ---------------------------------------------
            python_version=(platform.python_version()),
            operating_system=(platform.system() or "Unknown"),
            operating_system_version=(self._get_os_version()),
            architecture=(platform.machine() or "Unknown"),
            # ---------------------------------------------
            # CPU
            # ---------------------------------------------
            cpu_usage_percent=(
                psutil.cpu_percent(
                    interval=None,
                )
            ),
            cpu_physical_cores=(cpu_physical_cores),
            cpu_logical_cores=(cpu_logical_cores),
            # ---------------------------------------------
            # MEMORY
            # ---------------------------------------------
            memory_total_bytes=(memory.total),
            memory_used_bytes=(memory.used),
            memory_available_bytes=(memory.available),
            memory_usage_percent=(memory.percent),
            # ---------------------------------------------
            # DISK
            # ---------------------------------------------
            disk_total_bytes=(disk.total),
            disk_used_bytes=(disk.used),
            disk_free_bytes=(disk.free),
            disk_usage_percent=(disk.percent),
        )

    def _get_scheduler_status(
        self,
    ) -> SchedulerRuntimeStatus:
        """
        Resolve public scheduler runtime state.
        """

        if not self._scheduler.is_started:
            return SchedulerRuntimeStatus.STOPPED

        if self._scheduler.is_paused:
            return SchedulerRuntimeStatus.PAUSED

        return SchedulerRuntimeStatus.RUNNING

    @staticmethod
    def _get_os_version() -> str:
        """
        Return a human-readable host operating-system version.
        """

        release = platform.release()

        version = platform.version()

        if release and version:
            return f"{release} ({version})"

        return release or version or "Unknown"

    @staticmethod
    def _get_disk_root() -> str:
        """
        Return the filesystem root containing the running
        application.

        This keeps disk statistics relevant to the volume
        where the application is actually running.
        """

        path = Path.cwd().resolve()

        return path.anchor or "/"
