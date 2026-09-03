from __future__ import annotations

from aiogram import Router

from django_assistant_bot.bot.handlers.backups.menu import (
    router as menu_router,
)

router = Router(
    name="backups",
)

router.include_router(
    menu_router,
)


__all__ = [
    "router",
]
