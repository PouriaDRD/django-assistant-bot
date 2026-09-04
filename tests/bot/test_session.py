from __future__ import annotations

from typing import (
    cast,
)
from unittest.mock import (
    Mock,
    patch,
)
import pytest

from django_assistant_bot.services.settings import (
    ProxyConfigurationError,
)
from aiogram.client.session.aiohttp import (
    AiohttpSession,
)

from django_assistant_bot.bot.session import (
    build_telegram_session,
)
from django_assistant_bot.schemas.app_settings import (
    AppSettingsSchema,
)

# =========================================================
# DIRECT CONNECTION
# =========================================================


def test_build_session_without_proxy() -> None:
    settings = AppSettingsSchema(
        proxy_enabled=False,
        proxy_url="",
    )

    session_mock = Mock(
        spec=AiohttpSession,
    )

    with patch(
        ("django_assistant_bot.bot.session." "AiohttpSession"),
        return_value=session_mock,
    ) as session_factory:
        result = build_telegram_session(
            settings,
        )

    session_factory.assert_called_once_with()

    assert result is session_mock


def test_disabled_proxy_ignores_saved_url() -> None:
    settings = AppSettingsSchema(
        proxy_enabled=False,
        proxy_url=("socks5://127.0.0.1:1080"),
    )

    session_mock = Mock(
        spec=AiohttpSession,
    )

    with patch(
        ("django_assistant_bot.bot.session." "AiohttpSession"),
        return_value=session_mock,
    ) as session_factory:
        result = build_telegram_session(
            settings,
        )

    session_factory.assert_called_once_with()

    assert result is session_mock


# =========================================================
# PROXY CONNECTION
# =========================================================


def test_build_session_with_socks5_proxy() -> None:
    proxy_url = "socks5://127.0.0.1:1080"

    settings = AppSettingsSchema(
        proxy_enabled=True,
        proxy_url=proxy_url,
    )

    session_mock = Mock(
        spec=AiohttpSession,
    )

    with patch(
        ("django_assistant_bot.bot.session." "AiohttpSession"),
        return_value=session_mock,
    ) as session_factory:
        result = build_telegram_session(
            settings,
        )

    session_factory.assert_called_once_with(
        proxy=proxy_url,
    )

    assert result is session_mock


def test_build_session_with_http_proxy() -> None:
    proxy_url = "http://127.0.0.1:8080"

    settings = AppSettingsSchema(
        proxy_enabled=True,
        proxy_url=proxy_url,
    )

    with patch(
        ("django_assistant_bot.bot.session." "AiohttpSession"),
    ) as session_factory:
        build_telegram_session(
            settings,
        )

    session_factory.assert_called_once_with(
        proxy=proxy_url,
    )


def test_build_session_with_socks4_proxy() -> None:
    proxy_url = "socks4://127.0.0.1:1080"

    settings = AppSettingsSchema(
        proxy_enabled=True,
        proxy_url=proxy_url,
    )

    with patch(
        ("django_assistant_bot.bot.session." "AiohttpSession"),
    ) as session_factory:
        build_telegram_session(
            settings,
        )

    session_factory.assert_called_once_with(
        proxy=proxy_url,
    )


def test_proxy_credentials_are_passed_to_session() -> None:
    proxy_url = "socks5://user:" "secret@127.0.0.1:1080"

    settings = AppSettingsSchema(
        proxy_enabled=True,
        proxy_url=proxy_url,
    )

    with patch(
        ("django_assistant_bot.bot.session." "AiohttpSession"),
    ) as session_factory:
        build_telegram_session(
            settings,
        )

    session_factory.assert_called_once_with(
        proxy=proxy_url,
    )


# =========================================================
# DEFENSIVE FALLBACK
# =========================================================


def test_enabled_proxy_without_url_is_rejected() -> None:
    settings = cast(
        AppSettingsSchema,
        AppSettingsSchema().model_copy(
            update={
                "proxy_enabled": True,
                "proxy_url": "",
            },
        ),
    )

    with patch(
        ("django_assistant_bot.bot.session." "AiohttpSession"),
    ) as session_factory:
        with pytest.raises(
            ProxyConfigurationError,
        ):
            build_telegram_session(
                settings,
            )

    session_factory.assert_not_called()
