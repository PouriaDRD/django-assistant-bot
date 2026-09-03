from __future__ import annotations

from aiogram import Router

from django_assistant_bot.bot.handlers.projects.backup import (
    router as backup_router,
)
from django_assistant_bot.bot.handlers.projects.create import (
    router as create_router,
)
from django_assistant_bot.bot.handlers.projects.delete import (
    router as delete_router,
)
from django_assistant_bot.bot.handlers.projects.details import (
    router as details_router,
)
from django_assistant_bot.bot.handlers.projects.list import (
    router as list_router,
)
from django_assistant_bot.bot.handlers.projects.menu import (
    router as menu_router,
)
from django_assistant_bot.bot.handlers.projects.status import (
    router as status_router,
)

router = Router(
    name="projects",
)


router.include_router(
    menu_router,
)

router.include_router(
    create_router,
)

router.include_router(
    list_router,
)

router.include_router(
    details_router,
)

router.include_router(
    backup_router,
)

router.include_router(
    status_router,
)

router.include_router(
    delete_router,
)


__all__ = [
    "router",
]
