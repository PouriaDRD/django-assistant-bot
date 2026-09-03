from __future__ import annotations

from aiogram import Router

from django_assistant_bot.bot.handlers.common import (
    router as common_router,
)
from django_assistant_bot.bot.handlers.projects import (
    router as projects_router,
)

from django_assistant_bot.bot.handlers.backups import (
    router as backups_router,
)


def test_common_router_imports() -> None:
    assert isinstance(
        common_router,
        Router,
    )


def test_projects_router_imports() -> None:
    assert isinstance(
        projects_router,
        Router,
    )


def test_backup_history_router_is_registered() -> None:
    names = {router.name for router in backups_router.sub_routers}

    assert "backups.history" in names
