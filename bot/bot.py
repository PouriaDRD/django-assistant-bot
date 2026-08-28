from __future__ import annotations

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from bot.context import ApplicationContext
from bot.handlers.common import router as common_router
from bot.handlers.projects import router as projects_router
from bot.middlewares.auth import AdminAuthMiddleware


class TelegramBot:
    """
    Telegram bot application.
    """

    def __init__(
        self,
        context: ApplicationContext,
    ) -> None:
        config = context.config

        if not config.bot.token:
            raise ValueError("Telegram bot token is not configured.")

        self._context = context

        self._bot = Bot(
            token=config.bot.token,
            default=DefaultBotProperties(
                parse_mode=ParseMode.HTML,
            ),
        )

        self._dispatcher = Dispatcher(
            storage=MemoryStorage(),
        )

        self._auth_middleware = AdminAuthMiddleware(config)

        self._configure()

    @property
    def bot(self) -> Bot:
        return self._bot

    @property
    def dispatcher(self) -> Dispatcher:
        return self._dispatcher

    def _configure(self) -> None:
        self._dispatcher.message.middleware(
            self._auth_middleware,
        )

        self._dispatcher.callback_query.middleware(
            self._auth_middleware,
        )

        self._dispatcher.include_router(
            common_router,
        )

        self._dispatcher.include_router(
            projects_router,
        )

        self._dispatcher["context"] = self._context

    def update_context(
        self,
        context: ApplicationContext,
    ) -> None:
        self._context = context

        self._auth_middleware.update_config(
            context.config,
        )

        self._dispatcher["context"] = context

    async def start(self) -> None:
        await self._dispatcher.start_polling(
            self._bot,
        )

    async def stop(self) -> None:
        await self._bot.session.close()
