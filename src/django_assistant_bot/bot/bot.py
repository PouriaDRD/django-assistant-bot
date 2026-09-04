from __future__ import annotations

from aiogram import (
    Bot,
    Dispatcher,
)
from aiogram.client.default import (
    DefaultBotProperties,
)
from aiogram.enums import (
    ParseMode,
)
from aiogram.fsm.storage.memory import (
    MemoryStorage,
)

from django_assistant_bot.bot.context import (
    ApplicationContext,
)
from django_assistant_bot.bot.handlers.backups import (
    router as backups_router,
)
from django_assistant_bot.bot.handlers.common import (
    router as common_router,
)
from django_assistant_bot.bot.handlers.projects import (
    router as projects_router,
)
from django_assistant_bot.bot.handlers.scheduler import (
    router as scheduler_router,
)
from django_assistant_bot.bot.middlewares.auth import (
    AdminAuthMiddleware,
)


class TelegramBot:
    """
    Telegram bot application.

    The bot receives all runtime dependencies through
    ApplicationContext.
    """

    def __init__(
        self,
        context: ApplicationContext,
    ) -> None:
        self._context = context

        token = context.environment.telegram_bot_token.get_secret_value()

        self._bot = Bot(
            token=token,
            default=DefaultBotProperties(
                parse_mode=ParseMode.HTML,
            ),
        )

        self._dispatcher = Dispatcher(
            storage=MemoryStorage(),
        )

        self._auth_middleware = AdminAuthMiddleware(
            admin_service=(context.admins),
        )

        self._configure()

    @property
    def bot(
        self,
    ) -> Bot:
        return self._bot

    @property
    def dispatcher(
        self,
    ) -> Dispatcher:
        return self._dispatcher

    def _configure(
        self,
    ) -> None:
        """
        Configure middlewares, routers and dependencies.
        """

        self._dispatcher.message.middleware(
            self._auth_middleware,
        )

        self._dispatcher.callback_query.middleware(
            self._auth_middleware,
        )

        # -------------------------------------------------
        # ROUTERS
        # -------------------------------------------------

        self._dispatcher.include_router(
            common_router,
        )

        self._dispatcher.include_router(
            backups_router,
        )

        self._dispatcher.include_router(
            scheduler_router,
        )

        self._dispatcher.include_router(
            projects_router,
        )

        # -------------------------------------------------
        # DEPENDENCIES
        # -------------------------------------------------

        self._dispatcher["context"] = self._context

    async def start(
        self,
    ) -> None:
        """
        Start Telegram polling.
        """

        await self._dispatcher.start_polling(
            self._bot,
        )

    async def stop(
        self,
    ) -> None:
        """
        Close Telegram HTTP session.
        """

        await self._bot.session.close()
