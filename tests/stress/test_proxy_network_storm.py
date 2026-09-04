from __future__ import annotations

import asyncio
from types import (
    SimpleNamespace,
)
from unittest.mock import (
    AsyncMock,
    Mock,
    patch,
)

import pytest
from aiogram.exceptions import (
    TelegramBadRequest,
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
# CONFIGURATION
# =========================================================


CONCURRENT_CHECKS = 100

REPEATED_ROUNDS = 50

TEST_TOKEN = "123:test"

TEST_PROXY_URL = "socks5://username:super-secret-password@127.0.0.1:1080"


# =========================================================
# TEST DOUBLES
# =========================================================


class SessionFactory:
    """
    Create independent mocked sessions and retain them so
    cleanup can be asserted after a connection storm.
    """

    def __init__(
        self,
    ) -> None:
        self.sessions: list[Mock] = []

    def __call__(
        self,
        *,
        proxy: str,
    ) -> Mock:
        assert proxy == TEST_PROXY_URL

        session = Mock()

        session.close = AsyncMock()

        self.sessions.append(
            session,
        )

        return session


class MixedOutcomeBotFactory:
    """
    Produce bots with deterministic connection outcomes.

    Creation order:

    index % 5 == 0 -> success
    index % 5 == 1 -> network error
    index % 5 == 2 -> Telegram API error
    index % 5 == 3 -> unknown exception
    index % 5 == 4 -> timeout
    """

    def __init__(
        self,
    ) -> None:
        self.call_count = 0

    def __call__(
        self,
        *,
        token: str,
        session: object,
    ) -> Mock:
        del session

        assert token == TEST_TOKEN

        index = self.call_count

        self.call_count += 1

        outcome = index % 5

        bot = Mock()

        if outcome == 0:
            bot.get_me = AsyncMock(
                return_value=SimpleNamespace(
                    username=(f"stress_bot_{index}"),
                )
            )

            return bot

        if outcome == 1:
            bot.get_me = AsyncMock(
                side_effect=TelegramNetworkError(
                    method=GetMe(),
                    message="network unavailable",
                )
            )

            return bot

        if outcome == 2:
            bot.get_me = AsyncMock(
                side_effect=TelegramBadRequest(
                    method=GetMe(),
                    message="bad request",
                )
            )

            return bot

        if outcome == 3:
            bot.get_me = AsyncMock(
                side_effect=RuntimeError(("unexpected internal " "connection failure"))
            )

            return bot

        async def slow_get_me() -> None:
            await asyncio.sleep(
                1,
            )

        bot.get_me = AsyncMock(
            side_effect=slow_get_me,
        )

        return bot


# =========================================================
# CONCURRENT MIXED FAILURE STORM
# =========================================================


@pytest.mark.asyncio
async def test_many_proxy_connection_checks_survive_mixed_failure_storm() -> None:
    """
    Execute many proxy checks concurrently with mixed
    transport outcomes.

    Every connection check must return its own classified
    result without poisoning other checks.
    """

    session_factory = SessionFactory()

    bot_factory = MixedOutcomeBotFactory()

    with (
        patch(
            ("django_assistant_bot.bot." "proxy_connection.AiohttpSession"),
            side_effect=session_factory,
        ),
        patch(
            ("django_assistant_bot.bot." "proxy_connection.Bot"),
            side_effect=bot_factory,
        ),
    ):
        results = await asyncio.gather(
            *[
                check_telegram_proxy_connection(
                    token=TEST_TOKEN,
                    proxy_url=TEST_PROXY_URL,
                    timeout_seconds=0.01,
                )
                for _ in range(CONCURRENT_CHECKS)
            ]
        )

    # -----------------------------------------------------
    # ALL CHECKS RETURNED
    # -----------------------------------------------------

    assert len(results) == CONCURRENT_CHECKS

    assert bot_factory.call_count == (CONCURRENT_CHECKS)

    assert len(session_factory.sessions) == CONCURRENT_CHECKS

    # -----------------------------------------------------
    # EXPECTED DISTRIBUTION
    # -----------------------------------------------------

    counts = {
        status: sum(1 for result in results if result.status is status)
        for status in ProxyConnectionStatus
    }

    expected_per_status = CONCURRENT_CHECKS // 5

    assert counts[ProxyConnectionStatus.SUCCESS] == expected_per_status

    assert counts[ProxyConnectionStatus.NETWORK_ERROR] == expected_per_status

    assert counts[ProxyConnectionStatus.TELEGRAM_ERROR] == expected_per_status

    assert counts[ProxyConnectionStatus.UNKNOWN_ERROR] == expected_per_status

    assert counts[ProxyConnectionStatus.TIMEOUT] == expected_per_status

    # -----------------------------------------------------
    # EVERY TEMP SESSION MUST CLOSE
    # -----------------------------------------------------

    for session in session_factory.sessions:
        session.close.assert_awaited_once_with()


# =========================================================
# REPEATED NETWORK FAILURE RECOVERY
# =========================================================


@pytest.mark.asyncio
async def test_repeated_network_failures_do_not_poison_future_success() -> None:
    """
    Many consecutive network failures must not poison the
    function. A later healthy check must still succeed.
    """

    sessions: list[Mock] = []

    call_count = 0

    def session_factory(
        *,
        proxy: str,
    ) -> Mock:
        assert proxy == TEST_PROXY_URL

        session = Mock()

        session.close = AsyncMock()

        sessions.append(
            session,
        )

        return session

    def bot_factory(
        *,
        token: str,
        session: object,
    ) -> Mock:
        nonlocal call_count

        del session

        assert token == TEST_TOKEN

        bot = Mock()

        call_count += 1

        if call_count <= REPEATED_ROUNDS:
            bot.get_me = AsyncMock(
                side_effect=TelegramNetworkError(
                    method=GetMe(),
                    message="temporary outage",
                )
            )

            return bot

        bot.get_me = AsyncMock(
            return_value=SimpleNamespace(
                username="recovered_bot",
            )
        )

        return bot

    with (
        patch(
            ("django_assistant_bot.bot." "proxy_connection.AiohttpSession"),
            side_effect=session_factory,
        ),
        patch(
            ("django_assistant_bot.bot." "proxy_connection.Bot"),
            side_effect=bot_factory,
        ),
    ):
        failures = []

        for _ in range(REPEATED_ROUNDS):
            result = await check_telegram_proxy_connection(
                token=TEST_TOKEN,
                proxy_url=TEST_PROXY_URL,
                timeout_seconds=0.1,
            )

            failures.append(
                result,
            )

        recovered = await check_telegram_proxy_connection(
            token=TEST_TOKEN,
            proxy_url=TEST_PROXY_URL,
            timeout_seconds=0.1,
        )

    assert all(
        result.status is ProxyConnectionStatus.NETWORK_ERROR for result in failures
    )

    assert recovered.status is ProxyConnectionStatus.SUCCESS

    assert recovered.telegram_username == "recovered_bot"

    assert len(sessions) == (REPEATED_ROUNDS + 1)

    for session in sessions:
        session.close.assert_awaited_once_with()


# =========================================================
# TIMEOUT STORM
# =========================================================


@pytest.mark.asyncio
async def test_many_proxy_timeouts_release_all_temporary_sessions() -> None:
    """
    A timeout storm must not leak temporary Telegram
    sessions.
    """

    sessions: list[Mock] = []

    def session_factory(
        *,
        proxy: str,
    ) -> Mock:
        assert proxy == TEST_PROXY_URL

        session = Mock()

        session.close = AsyncMock()

        sessions.append(
            session,
        )

        return session

    def bot_factory(
        *,
        token: str,
        session: object,
    ) -> Mock:
        del session

        assert token == TEST_TOKEN

        bot = Mock()

        async def never_fast_enough() -> None:
            await asyncio.sleep(
                1,
            )

        bot.get_me = AsyncMock(
            side_effect=never_fast_enough,
        )

        return bot

    with (
        patch(
            ("django_assistant_bot.bot." "proxy_connection.AiohttpSession"),
            side_effect=session_factory,
        ),
        patch(
            ("django_assistant_bot.bot." "proxy_connection.Bot"),
            side_effect=bot_factory,
        ),
    ):
        results = await asyncio.gather(
            *[
                check_telegram_proxy_connection(
                    token=TEST_TOKEN,
                    proxy_url=TEST_PROXY_URL,
                    timeout_seconds=0.005,
                )
                for _ in range(CONCURRENT_CHECKS)
            ]
        )

    assert all(result.status is ProxyConnectionStatus.TIMEOUT for result in results)

    assert len(sessions) == CONCURRENT_CHECKS

    for session in sessions:
        session.close.assert_awaited_once_with()


# =========================================================
# SESSION CLOSE FAILURE
# =========================================================


@pytest.mark.asyncio
async def test_session_close_failure_does_not_replace_connection_result() -> None:
    """
    Failure while closing the temporary session must not
    replace an already-classified connection result.
    """

    session = Mock()

    session.close = AsyncMock(side_effect=RuntimeError("session close failure"))

    bot = Mock()

    bot.get_me = AsyncMock(
        side_effect=TelegramNetworkError(
            method=GetMe(),
            message="network failure",
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
            token=TEST_TOKEN,
            proxy_url=TEST_PROXY_URL,
        )

    assert result.status is ProxyConnectionStatus.NETWORK_ERROR

    session.close.assert_awaited_once_with()


# =========================================================
# CREDENTIAL LEAK PROTECTION
# =========================================================


@pytest.mark.asyncio
async def test_proxy_credentials_never_appear_in_failure_logs(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """
    Sensitive proxy credentials must never be written into
    logs during connection failures.
    """

    session = Mock()

    session.close = AsyncMock()

    bot = Mock()

    bot.get_me = AsyncMock(
        side_effect=RuntimeError(("connection failed through " f"{TEST_PROXY_URL}"))
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
            token=TEST_TOKEN,
            proxy_url=TEST_PROXY_URL,
        )

    assert result.status is ProxyConnectionStatus.UNKNOWN_ERROR

    combined_logs = "\n".join(record.getMessage() for record in caplog.records)

    assert TEST_PROXY_URL not in combined_logs

    assert "super-secret-password" not in combined_logs

    assert "username" not in combined_logs
