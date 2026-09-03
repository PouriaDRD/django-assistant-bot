from __future__ import annotations

from dataclasses import dataclass

from django_assistant_bot.core.environment import EnvironmentSettings
from django_assistant_bot.services.admin import AdminService
from django_assistant_bot.services.project import ProjectService
from django_assistant_bot.services.settings import AppSettingsService


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
