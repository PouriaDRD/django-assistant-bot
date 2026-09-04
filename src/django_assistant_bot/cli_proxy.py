from __future__ import annotations

from getpass import getpass
from urllib.parse import (
    urlsplit,
    urlunsplit,
)

from pydantic import (
    ValidationError,
)

from django_assistant_bot.bot.proxy_connection import (
    ProxyConnectionStatus,
    check_telegram_proxy_connection,
)
from django_assistant_bot.core.bootstrap import (
    bootstrap_application,
)
from django_assistant_bot.services.settings import (
    ProxyConfigurationError,
    SettingsPersistenceError,
)

# =========================================================
# EXIT CODES
# =========================================================


EXIT_SUCCESS = 0

EXIT_FAILURE = 1


# =========================================================
# MASKING
# =========================================================


def mask_proxy_url(
    proxy_url: str,
) -> str:
    """
    Mask proxy password for safe CLI display.
    """

    proxy_url = proxy_url.strip()

    if not proxy_url:
        return ""

    parsed = urlsplit(
        proxy_url,
    )

    hostname = parsed.hostname or ""

    if ":" in hostname:
        hostname = f"[{hostname}]"

    try:
        port = parsed.port

    except ValueError:
        port = None

    host = hostname

    if port is not None:
        host = f"{host}:{port}"

    if parsed.username is not None:
        username = parsed.username

        if parsed.password is not None:
            credentials = f"{username}:********"

        else:
            credentials = username

        host = f"{credentials}@{host}"

    return urlunsplit(
        (
            parsed.scheme,
            host,
            "",
            "",
            "",
        )
    )


# =========================================================
# STATUS
# =========================================================


def proxy_status_command() -> int:
    """
    Display persisted proxy configuration.
    """

    bootstrap = bootstrap_application()

    try:
        settings = bootstrap.context.settings.get_settings()

        status = "enabled" if settings.proxy_enabled else "disabled"

        print("Telegram proxy status")

        print(f"State: {status}")

        if settings.proxy_url:
            print(("URL: " f"{mask_proxy_url(settings.proxy_url)}"))

        else:
            print("URL: not configured")

        return EXIT_SUCCESS

    except SettingsPersistenceError:
        print("Failed to read proxy configuration.")

        return EXIT_FAILURE

    finally:
        bootstrap.engine.dispose()


# =========================================================
# SET
# =========================================================


def proxy_set_command(
    proxy_url: str | None = None,
) -> int:
    """
    Configure a new proxy URL.

    If no URL is passed through CLI arguments, the value is
    requested through getpass so credentials do not appear
    in terminal output or shell history.

    Changing the proxy URL always disables proxy usage until
    the new endpoint is successfully tested and enabled.
    """

    bootstrap = bootstrap_application()

    try:
        # -------------------------------------------------
        # SECURE INTERACTIVE INPUT
        # -------------------------------------------------

        if proxy_url is None:
            print(("Enter proxy URL below.\n" "Input is hidden for security."))

            proxy_url = getpass("Proxy URL: ")

        proxy_url = proxy_url.strip()

        if not proxy_url:
            print("Proxy URL cannot be empty.")

            return EXIT_FAILURE

        # -------------------------------------------------
        # PERSIST
        # -------------------------------------------------

        try:
            settings = bootstrap.context.settings.set_proxy_url(
                proxy_url,
            )

        except ValidationError:
            print(
                (
                    "Invalid proxy URL.\n"
                    "Supported schemes:\n"
                    "  http://host:port\n"
                    "  socks4://host:port\n"
                    "  socks5://host:port"
                )
            )

            return EXIT_FAILURE

        except SettingsPersistenceError:
            print(("Failed to save proxy " "configuration."))

            return EXIT_FAILURE

        print("Proxy URL saved successfully.")

        print("Proxy state: disabled")

        print(("Configured URL: " f"{mask_proxy_url(settings.proxy_url)}"))

        print(("Run 'py main.py proxy test' " "before enabling it."))

        return EXIT_SUCCESS

    finally:
        bootstrap.engine.dispose()


# =========================================================
# TEST
# =========================================================


async def proxy_test_command() -> int:
    """
    Test persisted proxy against Telegram Bot API.

    This command never changes proxy_enabled.
    """

    bootstrap = bootstrap_application()

    try:
        settings = bootstrap.context.settings.get_settings()

        if not settings.proxy_url:
            print("Proxy URL is not configured.")

            return EXIT_FAILURE

        token = bootstrap.environment.telegram_bot_token.get_secret_value()

        print("Testing Telegram proxy connection...")

        result = await check_telegram_proxy_connection(
            token=token,
            proxy_url=settings.proxy_url,
        )

        if result.is_successful:
            print("Proxy connection successful.")

            print(("Response time: " f"{result.duration_ms} ms"))

            if result.telegram_username:
                print(("Telegram bot: @" f"{result.telegram_username}"))

            return EXIT_SUCCESS

        if result.status is ProxyConnectionStatus.TIMEOUT:
            print(("Proxy connection failed: " "connection timed out."))

        elif result.status is ProxyConnectionStatus.NETWORK_ERROR:
            print(("Proxy connection failed: " "network error."))

        elif result.status is ProxyConnectionStatus.TELEGRAM_ERROR:
            print(("Proxy connection failed: " "Telegram API error."))

        else:
            print(("Proxy connection failed: " "unexpected transport error."))

        return EXIT_FAILURE

    except SettingsPersistenceError:
        print("Failed to read proxy configuration.")

        return EXIT_FAILURE

    finally:
        bootstrap.engine.dispose()


# =========================================================
# ENABLE
# =========================================================


async def proxy_enable_command() -> int:
    """
    Test and safely enable the configured proxy.

    Enabling is never persisted unless Telegram connectivity
    succeeds first.
    """

    bootstrap = bootstrap_application()

    try:
        settings = bootstrap.context.settings.get_settings()

        if not settings.proxy_url:
            print("Proxy URL is not configured.")

            return EXIT_FAILURE

        token = bootstrap.environment.telegram_bot_token.get_secret_value()

        print("Testing proxy before enabling...")

        result = await check_telegram_proxy_connection(
            token=token,
            proxy_url=settings.proxy_url,
        )

        if not result.is_successful:
            print(("Proxy was NOT enabled because " "the connection test failed."))

            return EXIT_FAILURE

        try:
            updated = bootstrap.context.settings.enable_proxy()

        except ProxyConfigurationError:
            print(("Proxy configuration is not " "valid for activation."))

            return EXIT_FAILURE

        except SettingsPersistenceError:
            print(
                (
                    "Connection test succeeded, "
                    "but proxy activation could "
                    "not be persisted."
                )
            )

            return EXIT_FAILURE

        if not updated.proxy_enabled:
            print(("Proxy activation did not " "complete successfully."))

            return EXIT_FAILURE

        print("Proxy enabled successfully.")

        print(("Restart the bot to apply " "the proxy transport."))

        return EXIT_SUCCESS

    except SettingsPersistenceError:
        print("Failed to read proxy configuration.")

        return EXIT_FAILURE

    finally:
        bootstrap.engine.dispose()


# =========================================================
# DISABLE
# =========================================================


def proxy_disable_command() -> int:
    """
    Disable proxy while preserving its URL.
    """

    bootstrap = bootstrap_application()

    try:
        settings = bootstrap.context.settings.disable_proxy()

        if settings.proxy_enabled:
            print("Proxy could not be disabled.")

            return EXIT_FAILURE

        print("Proxy disabled successfully.")

        if settings.proxy_url:
            print(
                (
                    "Configured URL was preserved: "
                    f"{mask_proxy_url(settings.proxy_url)}"
                )
            )

        print(("Start the bot again to use " "the direct Telegram connection."))

        return EXIT_SUCCESS

    except SettingsPersistenceError:
        print("Failed to disable proxy.")

        return EXIT_FAILURE

    finally:
        bootstrap.engine.dispose()


# =========================================================
# CLEAR
# =========================================================


def proxy_clear_command() -> int:
    """
    Disable proxy and remove its persisted URL.
    """

    bootstrap = bootstrap_application()

    try:
        settings = bootstrap.context.settings.clear_proxy()

        if settings.proxy_enabled or settings.proxy_url:
            print(("Proxy configuration could " "not be cleared completely."))

            return EXIT_FAILURE

        print("Proxy configuration cleared successfully.")

        print(
            ("The bot will use a direct " "Telegram connection on the " "next start.")
        )

        return EXIT_SUCCESS

    except SettingsPersistenceError:
        print(("Failed to clear proxy " "configuration."))

        return EXIT_FAILURE

    finally:
        bootstrap.engine.dispose()


# =========================================================
# EXPORTS
# =========================================================


__all__ = [
    "EXIT_FAILURE",
    "EXIT_SUCCESS",
    "mask_proxy_url",
    "proxy_clear_command",
    "proxy_disable_command",
    "proxy_enable_command",
    "proxy_set_command",
    "proxy_status_command",
    "proxy_test_command",
]
