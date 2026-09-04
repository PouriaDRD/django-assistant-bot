from __future__ import annotations

import logging
import asyncio
from aiohttp import (
    ClientError,
)
from aiohttp_socks import (
    ProxyConnectionError,
    ProxyError,
    ProxyTimeoutError,
)

from aiogram.exceptions import (
    TelegramNetworkError,
)
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
from aiogram.types import (
    BotCommand,
    BotCommandScopeAllPrivateChats,
    BotCommandScopeDefault,
)


from django_assistant_bot.bot.exceptions import (
    TelegramStartupError,
)
from django_assistant_bot.bot.context import (
    ApplicationContext,
)
from django_assistant_bot.bot.handlers.admins import (
    router as admins_router,
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
from django_assistant_bot.bot.handlers.proxy import (
    router as proxy_router,
)
from django_assistant_bot.bot.handlers.scheduler import (
    router as scheduler_router,
)
from django_assistant_bot.bot.handlers.settings import (
    router as settings_router,
)
from django_assistant_bot.bot.handlers.system_status import (
    router as system_status_router,
)
from django_assistant_bot.bot.middlewares.auth import (
    AdminAuthMiddleware,
)
from django_assistant_bot.bot.middlewares.bot_enabled import (
    BotEnabledMiddleware,
)
from django_assistant_bot.bot.session import (
    build_telegram_session,
)

# =========================================================
# LOGGER
# =========================================================


logger = logging.getLogger(
    __name__,
)


# =========================================================
# TELEGRAM BOT
# =========================================================


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

        # -------------------------------------------------
        # TELEGRAM HTTP SESSION
        # -------------------------------------------------

        settings = context.settings.get_settings()

        self._proxy_enabled = settings.proxy_enabled

        session = build_telegram_session(
            settings,
        )

        # -------------------------------------------------
        # BOT
        # -------------------------------------------------

        self._bot = Bot(
            token=token,
            session=session,
            default=DefaultBotProperties(
                parse_mode=ParseMode.HTML,
            ),
        )

        # -------------------------------------------------
        # DISPATCHER
        # -------------------------------------------------

        self._dispatcher = Dispatcher(
            storage=MemoryStorage(),
        )

        # -------------------------------------------------
        # MIDDLEWARES
        # -------------------------------------------------

        self._auth_middleware = AdminAuthMiddleware(
            admin_service=(context.admins),
        )

        self._bot_enabled_middleware = BotEnabledMiddleware(
            settings=(context.settings),
        )

        self._configure()

    # =====================================================
    # PROPERTIES
    # =====================================================

    @property
    def bot(
        self,
    ) -> Bot:
        """
        Return configured Telegram bot instance.
        """

        return self._bot

    @property
    def dispatcher(
        self,
    ) -> Dispatcher:
        """
        Return configured aiogram dispatcher.
        """

        return self._dispatcher

    # =====================================================
    # CONFIGURATION
    # =====================================================

    def _configure(
        self,
    ) -> None:
        """
        Configure middlewares, routers and dependencies.
        """

        # =================================================
        # MIDDLEWARES
        # =================================================

        # Authentication must run first so only authorized
        # administrators can access the application.
        self._dispatcher.message.middleware(
            self._auth_middleware,
        )

        # Global bot state is checked after authentication.
        self._dispatcher.message.middleware(
            self._bot_enabled_middleware,
        )

        self._dispatcher.callback_query.middleware(
            self._auth_middleware,
        )

        self._dispatcher.callback_query.middleware(
            self._bot_enabled_middleware,
        )

        # =================================================
        # ROUTERS
        # =================================================

        self._dispatcher.include_router(
            common_router,
        )

        self._dispatcher.include_router(
            settings_router,
        )

        self._dispatcher.include_router(
            proxy_router,
        )

        self._dispatcher.include_router(
            system_status_router,
        )

        self._dispatcher.include_router(
            admins_router,
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

        # =================================================
        # DEPENDENCIES
        # =================================================

        self._dispatcher["context"] = self._context

    # =====================================================
    # COMMANDS
    # =====================================================

    @staticmethod
    def _build_commands() -> list[BotCommand]:
        """
        Build Telegram command menu.
        """

        return [
            BotCommand(
                command="start",
                description="شروع و معرفی ربات",
            ),
            BotCommand(
                command="menu",
                description="نمایش منوی اصلی",
            ),
            BotCommand(
                command="help",
                description="نمایش راهنما",
            ),
        ]

    async def _clear_legacy_commands(
        self,
    ) -> None:
        """
        Remove legacy command sets.

        Telegram may keep different command lists for
        different scopes and languages. More specific
        command lists can override the default list.
        """

        default_scope = BotCommandScopeDefault()

        private_scope = BotCommandScopeAllPrivateChats()

        language_codes = (
            "fa",
            "en",
        )

        for language_code in language_codes:
            await self._bot.delete_my_commands(
                scope=default_scope,
                language_code=language_code,
            )

            await self._bot.delete_my_commands(
                scope=private_scope,
                language_code=language_code,
            )

        logger.info(("Legacy Telegram bot commands " "were cleared."))

    async def _register_commands(
        self,
    ) -> None:
        """
        Register canonical Telegram bot commands.

        Commands are registered both globally and for
        private chats to avoid legacy scope conflicts.
        """

        commands = self._build_commands()

        default_scope = BotCommandScopeDefault()

        private_scope = BotCommandScopeAllPrivateChats()

        await self._clear_legacy_commands()

        await self._bot.set_my_commands(
            commands=commands,
            scope=default_scope,
        )

        await self._bot.set_my_commands(
            commands=commands,
            scope=private_scope,
        )

        logger.info(("Telegram bot commands " "were registered."))

        await self._log_registered_commands(
            private_scope,
        )

    async def _log_registered_commands(
        self,
        scope: BotCommandScopeAllPrivateChats,
    ) -> None:
        """
        Read back and log registered Telegram commands.
        """

        commands = await self._bot.get_my_commands(
            scope=scope,
        )

        if not commands:
            logger.warning(("Telegram returned an empty " "command list."))
            return

        for command in commands:
            logger.info(
                ("Telegram command registered: " "/%s - %s"),
                command.command,
                command.description,
            )

    # =====================================================
    # LIFECYCLE
    # =====================================================

    async def start(self) -> None:
        """
        Register Telegram commands and start polling.

        Expected Telegram transport failures are converted into
        a sanitized application-level exception.

        Raw networking and proxy exception messages are never
        propagated because they may expose proxy endpoints,
        credentials, or other sensitive connection details.

        Programming errors and cancellation are intentionally
        allowed to propagate unchanged.
        """

        try:
            await self._register_commands()

            await self._dispatcher.start_polling(
                self._bot,
            )

        except asyncio.CancelledError:
            raise

        except (
            ProxyConnectionError,
            ProxyTimeoutError,
            ProxyError,
            TelegramNetworkError,
            ClientError,
            TimeoutError,
            ConnectionError,
        ):
            if self._proxy_enabled:
                raise TelegramStartupError(
                    ("Telegram startup failed while " "using the configured proxy.")
                ) from None

            raise TelegramStartupError(
                (
                    "Telegram startup failed because "
                    "the Telegram network connection "
                    "could not be established."
                )
            ) from None

    async def stop(self) -> None:
        """
        Close Telegram HTTP session.
        """

        await self._bot.session.close()


__all__ = [
    "TelegramBot",
]
