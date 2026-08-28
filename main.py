from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from bot.bot import TelegramBot
from bot.context import ApplicationContext
from config.settings_manager import SettingsManager
from utils.logger import setup_logging

CONFIG_PATH = Path("config.json")


async def run() -> None:
    setup_logging()

    logger = logging.getLogger(__name__)

    settings = SettingsManager(
        config_path=CONFIG_PATH,
    )

    config = settings.initialize()

    if not config.bot.enabled:
        logger.warning("Telegram bot is disabled in configuration.")
        return

    if not config.bot.token:
        logger.error("Telegram bot token is not configured.")
        return

    context = ApplicationContext(
        settings=settings,
        config=config,
    )

    telegram_bot = TelegramBot(
        context=context,
    )

    try:
        logger.info("Starting Django Backup Bot...")

        await telegram_bot.start()

    except (asyncio.CancelledError, KeyboardInterrupt):
        pass

    finally:
        logger.info("Stopping Django Backup Bot...")

        await telegram_bot.stop()


if __name__ == "__main__":
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        pass
