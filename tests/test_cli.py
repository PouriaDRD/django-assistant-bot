from __future__ import annotations

from collections.abc import (
    Coroutine,
)
from typing import (
    Any,
)
from unittest.mock import (
    AsyncMock,
    patch,
)

import pytest

from django_assistant_bot import (
    cli,
)
from django_assistant_bot.bot.exceptions import (
    TelegramStartupError,
)

# =========================================================
# DEFAULT APPLICATION
# =========================================================


def test_cli_runs_application_without_arguments() -> None:
    async def successful_run() -> None:
        return None

    with patch.object(
        cli,
        "run",
        successful_run,
    ):
        cli.main(
            [],
        )


# =========================================================
# PROXY COMMAND
# =========================================================


def test_cli_dispatches_proxy_status() -> None:
    proxy_status = AsyncMock(
        return_value=0,
    )

    with patch.object(
        cli,
        "run_proxy_command",
        proxy_status,
    ):
        cli.main(
            [
                "proxy",
                "status",
            ],
        )

    proxy_status.assert_awaited_once_with(
        "status",
        proxy_url=None,
    )


def test_cli_dispatches_proxy_set_with_url() -> None:
    proxy_set = AsyncMock(
        return_value=0,
    )

    proxy_url = "socks5://127.0.0.1:10808"

    with patch.object(
        cli,
        "run_proxy_command",
        proxy_set,
    ):
        cli.main(
            [
                "proxy",
                "set",
                proxy_url,
            ],
        )

    proxy_set.assert_awaited_once_with(
        "set",
        proxy_url=proxy_url,
    )


def test_cli_dispatches_proxy_set_without_url() -> None:
    proxy_set = AsyncMock(
        return_value=0,
    )

    with patch.object(
        cli,
        "run_proxy_command",
        proxy_set,
    ):
        cli.main(
            [
                "proxy",
                "set",
            ],
        )

    proxy_set.assert_awaited_once_with(
        "set",
        proxy_url=None,
    )


# =========================================================
# PROXY FAILURE EXIT
# =========================================================


def test_cli_exits_when_proxy_command_fails() -> None:
    proxy_command = AsyncMock(
        return_value=1,
    )

    with patch.object(
        cli,
        "run_proxy_command",
        proxy_command,
    ):
        with pytest.raises(
            SystemExit,
        ) as exc_info:
            cli.main(
                [
                    "proxy",
                    "test",
                ],
            )

    assert exc_info.value.code == 1


# =========================================================
# TELEGRAM STARTUP FAILURE
# =========================================================


def test_cli_exits_with_failure_on_telegram_startup_error() -> None:
    async def failing_run() -> None:
        raise TelegramStartupError(
            ("Telegram startup failed while " "using the configured proxy.")
        )

    with patch.object(
        cli,
        "run",
        failing_run,
    ):
        with pytest.raises(
            SystemExit,
        ) as exc_info:
            cli.main(
                [],
            )

    assert exc_info.value.code == 1


# =========================================================
# KEYBOARD INTERRUPT
# =========================================================


def test_cli_handles_keyboard_interrupt() -> None:
    def interrupted_run(
        coroutine: Coroutine[
            Any,
            Any,
            Any,
        ],
    ) -> None:
        coroutine.close()

        raise KeyboardInterrupt

    with patch.object(
        cli.asyncio,
        "run",
        interrupted_run,
    ):
        cli.main(
            [],
        )


# =========================================================
# PROGRAMMING ERROR
# =========================================================


def test_cli_does_not_hide_programming_errors() -> None:
    async def failing_run() -> None:
        raise AttributeError("real programming bug")

    with patch.object(
        cli,
        "run",
        failing_run,
    ):
        with pytest.raises(
            AttributeError,
            match="real programming bug",
        ):
            cli.main(
                [],
            )
