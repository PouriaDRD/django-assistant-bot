from __future__ import annotations

import asyncio
import logging

from django_assistant_bot.bot.bot import (
    TelegramBot,
)
from django_assistant_bot.core.bootstrap import (
    bootstrap_application,
)
from django_assistant_bot.utils.logger import (
    setup_logging,
)


async def run() -> None:
    """
    Start the Django Assistant Bot application.
    """

    setup_logging()

    logger = logging.getLogger(
        __name__,
    )

    bootstrap = bootstrap_application()

    context = bootstrap.context

    telegram_bot: TelegramBot | None = None

    try:
        app_settings = context.settings.get_settings()

        if not app_settings.bot_enabled:
            logger.warning("Telegram bot is disabled.")
            return

        telegram_bot = TelegramBot(
            context=context,
        )

        logger.info("Starting Django Assistant Bot...")

        await telegram_bot.start()

    except asyncio.CancelledError:
        logger.info("Application cancellation requested.")

        raise

    finally:
        logger.info("Stopping Django Assistant Bot...")

        if telegram_bot is not None:
            await telegram_bot.stop()

        bootstrap.engine.dispose()
