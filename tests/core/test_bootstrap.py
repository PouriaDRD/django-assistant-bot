from __future__ import annotations

from django_assistant_bot.core.bootstrap import (
    bootstrap_application,
)
from django_assistant_bot.services.admin import (
    AdminService,
)
from django_assistant_bot.services.backup import (
    BackupCoordinator,
)
from django_assistant_bot.services.project import (
    ProjectService,
)
from django_assistant_bot.services.settings import (
    AppSettingsService,
)


def test_application_bootstrap() -> None:
    bootstrap = bootstrap_application()

    try:
        assert bootstrap.engine is not None

        assert isinstance(
            bootstrap.context.projects,
            ProjectService,
        )

        assert isinstance(
            bootstrap.context.admins,
            AdminService,
        )

        assert isinstance(
            bootstrap.context.settings,
            AppSettingsService,
        )

        assert isinstance(
            bootstrap.context.backups,
            BackupCoordinator,
        )

    finally:
        bootstrap.engine.dispose()
