from __future__ import annotations

from dataclasses import dataclass

from django_assistant_bot.core.environment import (
    EnvironmentSettings,
)
from django_assistant_bot.services.admin import (
    AdminService,
)
from django_assistant_bot.services.backup import (
    BackupCoordinator,
    BackupHistoryService,
)
from django_assistant_bot.services.project import (
    ProjectService,
)
from django_assistant_bot.services.settings import (
    AppSettingsService,
)
from django_assistant_bot.services.scheduler import (
    BackupSchedulerService,
)


@dataclass(
    frozen=True,
    slots=True,
)
class ApplicationContext:
    """
    Runtime dependency container.

    Telegram handlers receive application services through
    this context instead of creating repositories or database
    dependencies themselves.
    """

    environment: EnvironmentSettings

    projects: ProjectService

    admins: AdminService

    settings: AppSettingsService

    backups: BackupCoordinator

    backup_history: BackupHistoryService

    scheduler: BackupSchedulerService
