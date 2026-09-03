from __future__ import annotations

from aiogram import Router

from django_assistant_bot.bot.handlers.common import (
    router as common_router,
)
from django_assistant_bot.bot.handlers.projects import (
    router as projects_router,
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
