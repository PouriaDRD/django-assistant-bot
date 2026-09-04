from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from enum import StrEnum
from time import perf_counter

from aiogram import Bot
from aiogram.client.session.aiohttp import (
    AiohttpSession,
)
from aiogram.exceptions import (
    TelegramAPIError,
    TelegramNetworkError,
)

# =========================================================
# LOGGER
# =========================================================


logger = logging.getLogger(
    __name__,
)


# =========================================================
# RESULT STATUS
# =========================================================


class ProxyConnectionStatus(
    StrEnum,
):
    """
    Result status for a Telegram proxy connection check.
    """

    SUCCESS = "success"

    TIMEOUT = "timeout"

    NETWORK_ERROR = "network_error"

    TELEGRAM_ERROR = "telegram_error"

    UNKNOWN_ERROR = "unknown_error"


# =========================================================
# RESULT
# =========================================================


@dataclass(
    frozen=True,
    slots=True,
)
class ProxyConnectionTestResult:
    """
    Result of a temporary Telegram connection through
    a configured proxy.

    Raw exception messages are intentionally not exposed
    because networking errors may contain sensitive proxy
    credentials.
    """

    status: ProxyConnectionStatus

    duration_ms: int

    telegram_username: str | None = None

    @property
    def is_successful(
        self,
    ) -> bool:
        return self.status is ProxyConnectionStatus.SUCCESS


# =========================================================
# CONNECTION CHECK
# =========================================================


async def check_telegram_proxy_connection(
    *,
    token: str,
    proxy_url: str,
    timeout_seconds: float = 10.0,
) -> ProxyConnectionTestResult:
    """
    Check Telegram Bot API connectivity through a proxy.

    A completely independent temporary HTTP session is
    created for the check.

    The application's active polling session is never
    modified.

    The temporary session is always closed afterwards.
    """

    started_at = perf_counter()

    session: AiohttpSession | None = None

    try:
        session = AiohttpSession(
            proxy=proxy_url,
        )

        bot = Bot(
            token=token,
            session=session,
        )

        async with asyncio.timeout(
            timeout_seconds,
        ):
            bot_info = await bot.get_me()

        duration_ms = int((perf_counter() - started_at) * 1000)

        logger.info(
            ("Telegram proxy connection check " "completed successfully in %s ms."),
            duration_ms,
        )

        return ProxyConnectionTestResult(
            status=(ProxyConnectionStatus.SUCCESS),
            duration_ms=duration_ms,
            telegram_username=(bot_info.username),
        )

    except TimeoutError:
        duration_ms = int((perf_counter() - started_at) * 1000)

        logger.warning(
            ("Telegram proxy connection check " "timed out after %s ms."),
            duration_ms,
        )

        return ProxyConnectionTestResult(
            status=(ProxyConnectionStatus.TIMEOUT),
            duration_ms=duration_ms,
        )

    except TelegramNetworkError as exc:
        duration_ms = int((perf_counter() - started_at) * 1000)

        # Never log str(exc).
        #
        # Networking errors may contain connection details
        # which can include sensitive proxy credentials.
        logger.warning(
            ("Telegram proxy connection check " "failed with network error: %s."),
            type(exc).__name__,
        )

        return ProxyConnectionTestResult(
            status=(ProxyConnectionStatus.NETWORK_ERROR),
            duration_ms=duration_ms,
        )

    except TelegramAPIError as exc:
        duration_ms = int((perf_counter() - started_at) * 1000)

        logger.warning(
            ("Telegram proxy connection check " "failed with Telegram API error: %s."),
            type(exc).__name__,
        )

        return ProxyConnectionTestResult(
            status=(ProxyConnectionStatus.TELEGRAM_ERROR),
            duration_ms=duration_ms,
        )

    except Exception as exc:
        duration_ms = int((perf_counter() - started_at) * 1000)

        logger.warning(
            ("Telegram proxy connection check " "failed unexpectedly: %s."),
            type(exc).__name__,
        )

        return ProxyConnectionTestResult(
            status=(ProxyConnectionStatus.UNKNOWN_ERROR),
            duration_ms=duration_ms,
        )

    finally:
        if session is not None:
            try:
                await session.close()

            except Exception as exc:
                logger.warning(
                    ("Could not close temporary " "Telegram proxy session: %s."),
                    type(exc).__name__,
                )


__all__ = [
    "ProxyConnectionStatus",
    "ProxyConnectionTestResult",
    "check_telegram_proxy_connection",
]
