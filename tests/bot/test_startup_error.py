from __future__ import annotations

import asyncio
from typing import (
    cast,
)
from unittest.mock import (
    AsyncMock,
    Mock,
)

import pytest
from aiohttp_socks import (
    ProxyConnectionError,
)

from django_assistant_bot.bot.bot import (
    TelegramBot,
)
from django_assistant_bot.bot.exceptions import (
    TelegramStartupError,
)

# =========================================================
# HELPER
# =========================================================


def build_telegram_bot_double(
    *,
    proxy_enabled: bool,
) -> TelegramBot:
    """
    Build a minimal TelegramBot test double without invoking
    the real constructor.
    """

    telegram_bot = cast(
        TelegramBot,
        object.__new__(TelegramBot),
    )

    setattr(
        telegram_bot,
        "_proxy_enabled",
        proxy_enabled,
    )

    setattr(
        telegram_bot,
        "_bot",
        Mock(),
    )

    dispatcher = Mock()

    dispatcher.start_polling = AsyncMock()

    setattr(
        telegram_bot,
        "_dispatcher",
        dispatcher,
    )

    setattr(
        telegram_bot,
        "_register_commands",
        AsyncMock(),
    )

    return telegram_bot


def get_register_commands(
    telegram_bot: TelegramBot,
) -> AsyncMock:
    """
    Return mocked command registration coroutine.
    """

    return cast(
        AsyncMock,
        getattr(
            telegram_bot,
            "_register_commands",
        ),
    )


# =========================================================
# PROXY FAILURE
# =========================================================


@pytest.mark.asyncio
async def test_proxy_startup_failure_is_sanitized() -> None:
    telegram_bot = build_telegram_bot_double(
        proxy_enabled=True,
    )

    register_commands = get_register_commands(
        telegram_bot,
    )

    register_commands.side_effect = ProxyConnectionError(
        ("Couldn't connect to " "socks5://user:" "SUPER_SECRET@127.0.0.1:1080")
    )

    with pytest.raises(
        TelegramStartupError,
    ) as exc_info:
        await telegram_bot.start()

    message = str(exc_info.value)

    assert message == ("Telegram startup failed while " "using the configured proxy.")

    assert "SUPER_SECRET" not in message

    assert "127.0.0.1" not in message

    assert "socks5://" not in message


# =========================================================
# DIRECT FAILURE
# =========================================================


@pytest.mark.asyncio
async def test_direct_startup_failure_is_sanitized() -> None:
    telegram_bot = build_telegram_bot_double(
        proxy_enabled=False,
    )

    register_commands = get_register_commands(
        telegram_bot,
    )

    register_commands.side_effect = ConnectionError("Sensitive network details")

    with pytest.raises(
        TelegramStartupError,
    ) as exc_info:
        await telegram_bot.start()

    message = str(exc_info.value)

    assert message == (
        "Telegram startup failed because "
        "the Telegram network connection "
        "could not be established."
    )

    assert "Sensitive network details" not in message


# =========================================================
# PROGRAMMING ERROR
# =========================================================


@pytest.mark.asyncio
async def test_programming_error_is_not_hidden() -> None:
    telegram_bot = build_telegram_bot_double(
        proxy_enabled=True,
    )

    register_commands = get_register_commands(
        telegram_bot,
    )

    register_commands.side_effect = AttributeError("real programming bug")

    with pytest.raises(
        AttributeError,
        match="real programming bug",
    ):
        await telegram_bot.start()


# =========================================================
# CANCELLATION
# =========================================================


@pytest.mark.asyncio
async def test_cancellation_is_not_converted() -> None:
    telegram_bot = build_telegram_bot_double(
        proxy_enabled=True,
    )

    register_commands = get_register_commands(
        telegram_bot,
    )

    register_commands.side_effect = asyncio.CancelledError()

    with pytest.raises(
        asyncio.CancelledError,
    ):
        await telegram_bot.start()
