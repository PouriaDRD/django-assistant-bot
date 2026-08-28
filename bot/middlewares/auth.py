from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject, User

from config.models import AppConfig

Handler = Callable[
    [TelegramObject, dict[str, Any]],
    Awaitable[Any],
]


class AdminAuthMiddleware(BaseMiddleware):
    """
    Allows Telegram updates only for configured administrators.
    """

    def __init__(self, config: AppConfig) -> None:
        self._config = config

    def update_config(
        self,
        config: AppConfig,
    ) -> None:
        self._config = config

    async def __call__(
        self,
        handler: Handler,
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user: User | None = data.get("event_from_user")

        if user is None:
            return None

        if user.id not in self._config.admins:
            if isinstance(event, Message):
                await event.answer("⛔️ شما مجاز به استفاده از این ربات نیستید.")
            elif isinstance(event, CallbackQuery):
                await event.answer(
                    "⛔️ شما مجاز به استفاده از این ربات نیستید.",
                    show_alert=True,
                )
            return None

        return await handler(event, data)
