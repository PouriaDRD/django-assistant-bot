from __future__ import annotations

import logging

from aiogram.client.session.aiohttp import (
    AiohttpSession,
)

from django_assistant_bot.schemas.app_settings import (
    AppSettingsSchema,
)
from django_assistant_bot.services.settings import (
    ProxyConfigurationError,
)

# =========================================================
# LOGGER
# =========================================================


logger = logging.getLogger(
    __name__,
)


# =========================================================
# SESSION FACTORY
# =========================================================


def build_telegram_session(
    settings: AppSettingsSchema,
) -> AiohttpSession:
    """
    Build the HTTP session used by aiogram.

    Security invariant:

    If proxy usage is explicitly enabled, Telegram traffic
    must never silently fall back to a direct connection.

    Runtime proxy changes require application restart because
    the HTTP connector is created once for the Bot lifecycle.
    """

    if not settings.proxy_enabled:
        logger.info("Telegram proxy is disabled.")

        return AiohttpSession()

    if not settings.proxy_url:
        logger.error(
            (
                "Telegram proxy is enabled but no proxy URL "
                "is configured. Direct fallback is refused."
            )
        )

        raise ProxyConfigurationError(
            ("Telegram proxy is enabled but no " "proxy URL is configured.")
        )

    logger.info("Telegram proxy is enabled.")

    return AiohttpSession(
        proxy=settings.proxy_url,
    )


__all__ = [
    "build_telegram_session",
]
