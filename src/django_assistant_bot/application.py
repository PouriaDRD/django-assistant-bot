from __future__ import annotations

import asyncio
import logging

from django_assistant_bot.bot.bot import (
    TelegramBot,
)
from django_assistant_bot.bot.delivery import (
    TelegramBackupDelivery,
)
from django_assistant_bot.core.bootstrap import (
    bootstrap_application,
)
from django_assistant_bot.services.delivery import (
    BackupDeliveryService,
)
from django_assistant_bot.utils.logger import (
    setup_logging,
)


async def run() -> None:
    """
    Start the Django Assistant Bot application.

    Telegram polling always remains available so an
    authorized administrator can re-enable the application
    after it has been globally disabled.
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

        # -------------------------------------------------
        # TELEGRAM BOT
        # -------------------------------------------------

        telegram_bot = TelegramBot(
            context=context,
        )

        # -------------------------------------------------
        # DELIVERY
        # -------------------------------------------------

        telegram_delivery = TelegramBackupDelivery(
            bot=telegram_bot.bot,
            admins=context.admins,
        )

        backup_delivery = BackupDeliveryService(
            telegram_delivery,
        )

        context.scheduler.set_delivery(
            backup_delivery,
        )

        # -------------------------------------------------
        # SCHEDULER
        # -------------------------------------------------

        if app_settings.bot_enabled:
            context.scheduler.start()

        else:
            logger.warning(
                (
                    "Application is disabled. "
                    "Telegram polling remains active "
                    "for re-enabling."
                )
            )

        # -------------------------------------------------
        # TELEGRAM
        # -------------------------------------------------

        logger.info("Starting Django Assistant Bot...")

        await telegram_bot.start()

    except asyncio.CancelledError:
        logger.info("Application cancellation requested.")

        raise

    finally:
        logger.info("Stopping Django Assistant Bot...")

        if context.scheduler.is_started:
            context.scheduler.stop(
                wait=False,
            )

        if telegram_bot is not None:
            await telegram_bot.stop()

        bootstrap.engine.dispose()
