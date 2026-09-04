from __future__ import annotations

import argparse
import asyncio
import logging
from collections.abc import (
    Sequence,
)
from typing import (
    cast,
)

from django_assistant_bot.application import (
    run,
)
from django_assistant_bot.bot.exceptions import (
    TelegramStartupError,
)
from django_assistant_bot.cli_proxy import (
    EXIT_FAILURE,
    EXIT_SUCCESS,
    proxy_clear_command,
    proxy_disable_command,
    proxy_enable_command,
    proxy_set_command,
    proxy_status_command,
    proxy_test_command,
)

# =========================================================
# LOGGER
# =========================================================


logger = logging.getLogger(
    __name__,
)


# =========================================================
# PARSER
# =========================================================


def build_parser() -> argparse.ArgumentParser:
    """
    Build application command-line parser.
    """

    parser = argparse.ArgumentParser(
        prog="django-assistant-bot",
        description=("Django Assistant Bot management CLI."),
    )

    commands = parser.add_subparsers(
        dest="command",
    )

    # =====================================================
    # PROXY
    # =====================================================

    proxy_parser = commands.add_parser(
        "proxy",
        help=("Manage Telegram proxy configuration."),
    )

    proxy_commands = proxy_parser.add_subparsers(
        dest="proxy_action",
    )

    proxy_commands.add_parser(
        "status",
        help=("Show persisted proxy status."),
    )

    # -----------------------------------------------------
    # SET
    # -----------------------------------------------------

    proxy_set_parser = proxy_commands.add_parser(
        "set",
        help=("Configure a proxy URL."),
    )

    proxy_set_parser.add_argument(
        "proxy_url",
        nargs="?",
        default=None,
        help=("Optional proxy URL. " "If omitted, secure hidden input is used."),
    )

    # -----------------------------------------------------
    # TEST
    # -----------------------------------------------------

    proxy_commands.add_parser(
        "test",
        help=("Test configured proxy against Telegram."),
    )

    # -----------------------------------------------------
    # ENABLE
    # -----------------------------------------------------

    proxy_commands.add_parser(
        "enable",
        help=("Test and safely enable configured proxy."),
    )

    # -----------------------------------------------------
    # DISABLE
    # -----------------------------------------------------

    proxy_commands.add_parser(
        "disable",
        help=("Disable proxy while preserving its URL."),
    )

    # -----------------------------------------------------
    # CLEAR
    # -----------------------------------------------------

    proxy_commands.add_parser(
        "clear",
        help=("Disable proxy and remove its URL."),
    )

    return parser


# =========================================================
# PROXY COMMAND DISPATCH
# =========================================================


async def run_proxy_command(
    action: str | None,
    *,
    proxy_url: str | None = None,
) -> int:
    """
    Execute one proxy management command.
    """

    if action == "status":
        return proxy_status_command()

    if action == "set":
        return proxy_set_command(
            proxy_url,
        )

    if action == "test":
        return await proxy_test_command()

    if action == "enable":
        return await proxy_enable_command()

    if action == "disable":
        return proxy_disable_command()

    if action == "clear":
        return proxy_clear_command()

    print(
        (
            "Missing proxy command.\n"
            "\n"
            "Available commands:\n"
            "  status\n"
            "  set [proxy_url]\n"
            "  test\n"
            "  enable\n"
            "  disable\n"
            "  clear"
        )
    )

    return EXIT_FAILURE


# =========================================================
# APPLICATION DISPATCH
# =========================================================


async def run_cli(
    argv: Sequence[str] | None = None,
) -> int:
    """
    Dispatch normal application startup or management CLI.
    """

    parser = build_parser()

    args = parser.parse_args(
        argv,
    )

    command = cast(
        str | None,
        getattr(
            args,
            "command",
            None,
        ),
    )

    # -----------------------------------------------------
    # NORMAL BOT STARTUP
    # -----------------------------------------------------

    if command is None:
        await run()

        return EXIT_SUCCESS

    # -----------------------------------------------------
    # PROXY
    # -----------------------------------------------------

    if command == "proxy":
        action = cast(
            str | None,
            getattr(
                args,
                "proxy_action",
                None,
            ),
        )

        proxy_url = cast(
            str | None,
            getattr(
                args,
                "proxy_url",
                None,
            ),
        )

        return await run_proxy_command(
            action,
            proxy_url=proxy_url,
        )

    return EXIT_FAILURE


# =========================================================
# ENTRYPOINT
# =========================================================


def main(
    argv: Sequence[str] | None = None,
) -> None:
    """
    Run application CLI.
    """

    try:
        exit_code = asyncio.run(
            run_cli(
                argv,
            )
        )

    except KeyboardInterrupt:
        return

    except TelegramStartupError as exc:
        logger.critical(
            "%s",
            exc,
        )

        raise SystemExit(EXIT_FAILURE) from None

    if exit_code != EXIT_SUCCESS:
        raise SystemExit(exit_code)


# =========================================================
# EXPORTS
# =========================================================


__all__ = [
    "build_parser",
    "main",
    "run_cli",
    "run_proxy_command",
]
