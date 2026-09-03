from __future__ import annotations

from collections.abc import (
    Awaitable,
    Callable,
)
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import (
    CallbackQuery,
    Message,
    TelegramObject,
    User,
)

from django_assistant_bot.services.admin import (
    AdminPersistenceError,
    AdminService,
)

Handler = Callable[
    [
        TelegramObject,
        dict[str, Any],
    ],
    Awaitable[Any],
]


class AdminAuthMiddleware(BaseMiddleware):
    """
    Restrict Telegram access to registered administrators.

    Administrator information is read from SQLite through
    AdminService instead of being cached from JSON config.
    """

    def __init__(
        self,
        admin_service: AdminService,
    ) -> None:
        self._admin_service = admin_service

    async def __call__(
        self,
        handler: Handler,
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user: User | None = data.get("event_from_user")

        if user is None:
            return None

        try:
            is_admin = self._admin_service.is_admin(
                user.id,
            )

        except AdminPersistenceError:
            await self._deny(
                event=event,
                message=("⚠️ خطایی هنگام بررسی " "دسترسی رخ داد."),
            )

            return None

        if not is_admin:
            await self._deny(
                event=event,
                message=("⛔️ شما مجاز به استفاده " "از این ربات نیستید."),
            )

            return None

        return await handler(
            event,
            data,
        )

    @staticmethod
    async def _deny(
        *,
        event: TelegramObject,
        message: str,
    ) -> None:
        if isinstance(
            event,
            Message,
        ):
            await event.answer(
                message,
            )

            return

        if isinstance(
            event,
            CallbackQuery,
        ):
            await event.answer(
                message,
                show_alert=True,
            )
