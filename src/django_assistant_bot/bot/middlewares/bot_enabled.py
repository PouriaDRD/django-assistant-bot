from __future__ import annotations

from collections.abc import (
    Awaitable,
    Callable,
)
from typing import (
    Any,
    Protocol,
)

from aiogram import BaseMiddleware
from aiogram.types import (
    CallbackQuery,
    Message,
    TelegramObject,
)

from django_assistant_bot.bot.keyboards.settings import (
    BOT_ENABLE_CALLBACK,
    disabled_bot_keyboard,
)
from django_assistant_bot.services.settings import (
    SettingsPersistenceError,
)

Handler = Callable[
    [
        TelegramObject,
        dict[str, Any],
    ],
    Awaitable[Any],
]


# =========================================================
# DEPENDENCY CONTRACT
# =========================================================


class BotSettingsReader(Protocol):
    """
    Minimal settings dependency required by the middleware.
    """

    def is_bot_enabled(
        self,
    ) -> bool: ...


# =========================================================
# MIDDLEWARE
# =========================================================


class BotEnabledMiddleware(BaseMiddleware):
    """
    Block Telegram activity while the application is
    globally disabled.

    Important:
    - Telegram polling stays alive.
    - Admin authentication is handled by another middleware.
    - The only callback allowed while disabled is the
      callback responsible for enabling the bot again.
    """

    def __init__(
        self,
        settings: BotSettingsReader,
    ) -> None:
        self._settings = settings

    async def __call__(
        self,
        handler: Handler,
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        """
        Allow normal execution only while the application is
        enabled.

        When disabled, only BOT_ENABLE_CALLBACK may reach its
        handler.
        """

        try:
            bot_enabled = self._settings.is_bot_enabled()

        except SettingsPersistenceError:
            await self._send_settings_error(event)

            return None

        if bot_enabled:
            return await handler(
                event,
                data,
            )

        if self._is_enable_callback(event):
            return await handler(
                event,
                data,
            )

        await self._deny(event)

        return None

    # =====================================================
    # HELPERS
    # =====================================================

    @staticmethod
    def _is_enable_callback(
        event: TelegramObject,
    ) -> bool:
        """
        Return whether the event is the one permitted action
        while the application is disabled.
        """

        return (
            isinstance(
                event,
                CallbackQuery,
            )
            and event.data == BOT_ENABLE_CALLBACK
        )

    @staticmethod
    async def _deny(
        event: TelegramObject,
    ) -> None:
        """
        Inform the administrator that the bot is disabled.
        """

        if isinstance(
            event,
            Message,
        ):
            await event.answer(
                (
                    "🔴 <b>ربات غیرفعال است</b>\n"
                    "\n"
                    "تمام فعالیت‌های ربات در حال حاضر "
                    "متوقف هستند.\n"
                    "\n"
                    "برای استفاده مجدد، ابتدا ربات را "
                    "فعال کنید."
                ),
                reply_markup=(disabled_bot_keyboard()),
            )

            return

        if isinstance(
            event,
            CallbackQuery,
        ):
            await event.answer(
                ("🔴 ربات غیرفعال است.\n" "ابتدا ربات را فعال کنید."),
                show_alert=True,
            )

    @staticmethod
    async def _send_settings_error(
        event: TelegramObject,
    ) -> None:
        """
        Fail closed when runtime settings cannot be read.
        """

        message = "⚠️ خطا در بررسی وضعیت ربات."

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


__all__ = [
    "BotEnabledMiddleware",
]
