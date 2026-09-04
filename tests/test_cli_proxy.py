from __future__ import annotations

from types import (
    SimpleNamespace,
)
from unittest.mock import (
    AsyncMock,
    Mock,
    patch,
)

import pytest
from pydantic import (
    SecretStr,
)

from django_assistant_bot import (
    cli_proxy,
)
from django_assistant_bot.bot.proxy_connection import (
    ProxyConnectionStatus,
    ProxyConnectionTestResult,
)
from django_assistant_bot.schemas.app_settings import (
    AppSettingsSchema,
)

# =========================================================
# BOOTSTRAP DOUBLE
# =========================================================


def build_bootstrap_double(
    settings: AppSettingsSchema,
) -> SimpleNamespace:
    settings_service = Mock()

    settings_service.get_settings.return_value = settings

    settings_service.set_proxy_url.return_value = settings.model_copy(
        update={
            "proxy_enabled": False,
        },
    )

    settings_service.disable_proxy.return_value = settings.model_copy(
        update={
            "proxy_enabled": False,
        },
    )

    settings_service.clear_proxy.return_value = settings.model_copy(
        update={
            "proxy_enabled": False,
            "proxy_url": "",
        },
    )

    settings_service.enable_proxy.return_value = settings.model_copy(
        update={
            "proxy_enabled": True,
        },
    )

    engine = Mock()

    environment = SimpleNamespace(
        telegram_bot_token=SecretStr(
            "123:test-token",
        ),
    )

    context = SimpleNamespace(
        settings=settings_service,
    )

    return SimpleNamespace(
        context=context,
        environment=environment,
        engine=engine,
    )


# =========================================================
# MASKING
# =========================================================


def test_proxy_password_is_masked() -> None:
    result = cli_proxy.mask_proxy_url(("socks5://user:" "SUPER_SECRET@127.0.0.1:1080"))

    assert result == ("socks5://user:" "********@127.0.0.1:1080")

    assert "SUPER_SECRET" not in result


# =========================================================
# STATUS
# =========================================================


def test_proxy_status_command() -> None:
    settings = AppSettingsSchema(
        proxy_enabled=True,
        proxy_url=("socks5://user:" "secret@127.0.0.1:1080"),
    )

    bootstrap = build_bootstrap_double(
        settings,
    )

    with patch.object(
        cli_proxy,
        "bootstrap_application",
        return_value=bootstrap,
    ):
        exit_code = cli_proxy.proxy_status_command()

    assert exit_code == 0

    bootstrap.engine.dispose.assert_called_once_with()


# =========================================================
# SET
# =========================================================


def test_proxy_set_command_uses_secure_prompt() -> None:
    settings = AppSettingsSchema(
        proxy_enabled=True,
        proxy_url=("socks5://127.0.0.1:1080"),
    )

    bootstrap = build_bootstrap_double(
        settings,
    )

    new_proxy = "socks5://127.0.0.1:1081"

    bootstrap.context.settings.set_proxy_url.return_value = AppSettingsSchema(
        proxy_enabled=False,
        proxy_url=new_proxy,
    )

    with (
        patch.object(
            cli_proxy,
            "bootstrap_application",
            return_value=bootstrap,
        ),
        patch.object(
            cli_proxy,
            "getpass",
            return_value=new_proxy,
        ) as secure_prompt,
    ):
        exit_code = cli_proxy.proxy_set_command()

    assert exit_code == 0

    secure_prompt.assert_called_once_with("Proxy URL: ")

    bootstrap.context.settings.set_proxy_url.assert_called_once_with(
        new_proxy,
    )

    bootstrap.engine.dispose.assert_called_once_with()


# =========================================================
# DISABLE RECOVERY
# =========================================================


def test_proxy_disable_command_recovers_from_enabled_proxy() -> None:
    settings = AppSettingsSchema(
        proxy_enabled=True,
        proxy_url=("socks5://127.0.0.1:1080"),
    )

    bootstrap = build_bootstrap_double(
        settings,
    )

    with patch.object(
        cli_proxy,
        "bootstrap_application",
        return_value=bootstrap,
    ):
        exit_code = cli_proxy.proxy_disable_command()

    assert exit_code == 0

    bootstrap.context.settings.disable_proxy.assert_called_once_with()

    bootstrap.engine.dispose.assert_called_once_with()


# =========================================================
# CLEAR RECOVERY
# =========================================================


def test_proxy_clear_command_removes_proxy() -> None:
    settings = AppSettingsSchema(
        proxy_enabled=True,
        proxy_url=("socks5://127.0.0.1:1080"),
    )

    bootstrap = build_bootstrap_double(
        settings,
    )

    with patch.object(
        cli_proxy,
        "bootstrap_application",
        return_value=bootstrap,
    ):
        exit_code = cli_proxy.proxy_clear_command()

    assert exit_code == 0

    bootstrap.context.settings.clear_proxy.assert_called_once_with()

    bootstrap.engine.dispose.assert_called_once_with()


# =========================================================
# TEST SUCCESS
# =========================================================


@pytest.mark.asyncio
async def test_proxy_test_command_success() -> None:
    settings = AppSettingsSchema(
        proxy_enabled=False,
        proxy_url=("socks5://127.0.0.1:1080"),
    )

    bootstrap = build_bootstrap_double(
        settings,
    )

    result = ProxyConnectionTestResult(
        status=(ProxyConnectionStatus.SUCCESS),
        duration_ms=120,
        telegram_username="test_bot",
    )

    with (
        patch.object(
            cli_proxy,
            "bootstrap_application",
            return_value=bootstrap,
        ),
        patch.object(
            cli_proxy,
            "check_telegram_proxy_connection",
            new=AsyncMock(
                return_value=result,
            ),
        ) as connection_check,
    ):
        exit_code = await cli_proxy.proxy_test_command()

    assert exit_code == 0

    connection_check.assert_awaited_once_with(
        token="123:test-token",
        proxy_url=("socks5://127.0.0.1:1080"),
    )

    bootstrap.engine.dispose.assert_called_once_with()


# =========================================================
# ENABLE SUCCESS
# =========================================================


@pytest.mark.asyncio
async def test_proxy_enable_requires_successful_connection() -> None:
    settings = AppSettingsSchema(
        proxy_enabled=False,
        proxy_url=("socks5://127.0.0.1:1080"),
    )

    bootstrap = build_bootstrap_double(
        settings,
    )

    result = ProxyConnectionTestResult(
        status=(ProxyConnectionStatus.SUCCESS),
        duration_ms=100,
    )

    with (
        patch.object(
            cli_proxy,
            "bootstrap_application",
            return_value=bootstrap,
        ),
        patch.object(
            cli_proxy,
            "check_telegram_proxy_connection",
            new=AsyncMock(
                return_value=result,
            ),
        ),
    ):
        exit_code = await cli_proxy.proxy_enable_command()

    assert exit_code == 0

    bootstrap.context.settings.enable_proxy.assert_called_once_with()

    bootstrap.engine.dispose.assert_called_once_with()


# =========================================================
# ENABLE FAILURE
# =========================================================


@pytest.mark.asyncio
async def test_failed_connection_never_enables_proxy() -> None:
    settings = AppSettingsSchema(
        proxy_enabled=False,
        proxy_url=("socks5://127.0.0.1:1080"),
    )

    bootstrap = build_bootstrap_double(
        settings,
    )

    result = ProxyConnectionTestResult(
        status=(ProxyConnectionStatus.NETWORK_ERROR),
        duration_ms=100,
    )

    with (
        patch.object(
            cli_proxy,
            "bootstrap_application",
            return_value=bootstrap,
        ),
        patch.object(
            cli_proxy,
            "check_telegram_proxy_connection",
            new=AsyncMock(
                return_value=result,
            ),
        ),
    ):
        exit_code = await cli_proxy.proxy_enable_command()

    assert exit_code == 1

    bootstrap.context.settings.enable_proxy.assert_not_called()

    bootstrap.engine.dispose.assert_called_once_with()
