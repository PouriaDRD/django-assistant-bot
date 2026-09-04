from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import (
    AsyncMock,
    Mock,
    patch,
)

import pytest
from aiogram.exceptions import (
    TelegramNetworkError,
)
from aiogram.methods import (
    GetMe,
)

from django_assistant_bot.bot.proxy_connection import (
    ProxyConnectionStatus,
    check_telegram_proxy_connection,
)

# =========================================================
# SUCCESS
# =========================================================


@pytest.mark.asyncio
async def test_proxy_connection_success() -> None:
    session = Mock()

    session.close = AsyncMock()

    bot = Mock()

    bot.get_me = AsyncMock(
        return_value=SimpleNamespace(
            username="test_bot",
        )
    )

    with (
        patch(
            ("django_assistant_bot.bot." "proxy_connection.AiohttpSession"),
            return_value=session,
        ) as session_factory,
        patch(
            ("django_assistant_bot.bot." "proxy_connection.Bot"),
            return_value=bot,
        ),
    ):
        result = await check_telegram_proxy_connection(
            token="123:test",
            proxy_url=("socks5://127.0.0.1:1080"),
        )

    session_factory.assert_called_once_with(
        proxy="socks5://127.0.0.1:1080",
    )

    bot.get_me.assert_awaited_once_with()

    session.close.assert_awaited_once_with()

    assert result.is_successful is True

    assert result.status is ProxyConnectionStatus.SUCCESS

    assert result.telegram_username == "test_bot"


# =========================================================
# NETWORK FAILURE
# =========================================================


@pytest.mark.asyncio
async def test_proxy_connection_network_failure() -> None:
    session = Mock()

    session.close = AsyncMock()

    bot = Mock()

    bot.get_me = AsyncMock(
        side_effect=TelegramNetworkError(
            method=GetMe(),
            message="network failed",
        )
    )

    with (
        patch(
            ("django_assistant_bot.bot." "proxy_connection.AiohttpSession"),
            return_value=session,
        ),
        patch(
            ("django_assistant_bot.bot." "proxy_connection.Bot"),
            return_value=bot,
        ),
    ):
        result = await check_telegram_proxy_connection(
            token="123:test",
            proxy_url=("socks5://127.0.0.1:1080"),
        )

    assert result.is_successful is False

    assert result.status is ProxyConnectionStatus.NETWORK_ERROR

    session.close.assert_awaited_once_with()


# =========================================================
# TIMEOUT
# =========================================================


@pytest.mark.asyncio
async def test_proxy_connection_timeout() -> None:
    session = Mock()

    session.close = AsyncMock()

    async def slow_get_me() -> None:
        import asyncio

        await asyncio.sleep(
            0.05,
        )

    bot = Mock()

    bot.get_me = AsyncMock(
        side_effect=slow_get_me,
    )

    with (
        patch(
            ("django_assistant_bot.bot." "proxy_connection.AiohttpSession"),
            return_value=session,
        ),
        patch(
            ("django_assistant_bot.bot." "proxy_connection.Bot"),
            return_value=bot,
        ),
    ):
        result = await check_telegram_proxy_connection(
            token="123:test",
            proxy_url=("socks5://127.0.0.1:1080"),
            timeout_seconds=0.001,
        )

    assert result.status is ProxyConnectionStatus.TIMEOUT

    assert result.is_successful is False

    session.close.assert_awaited_once_with()


# =========================================================
# SESSION CLEANUP
# =========================================================


@pytest.mark.asyncio
async def test_proxy_check_always_closes_session() -> None:
    session = Mock()

    session.close = AsyncMock()

    bot = Mock()

    bot.get_me = AsyncMock(side_effect=RuntimeError("unexpected failure"))

    with (
        patch(
            ("django_assistant_bot.bot." "proxy_connection.AiohttpSession"),
            return_value=session,
        ),
        patch(
            ("django_assistant_bot.bot." "proxy_connection.Bot"),
            return_value=bot,
        ),
    ):
        result = await check_telegram_proxy_connection(
            token="123:test",
            proxy_url=("socks5://127.0.0.1:1080"),
        )

    assert result.status is ProxyConnectionStatus.UNKNOWN_ERROR

    session.close.assert_awaited_once_with()
