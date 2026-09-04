from __future__ import annotations

from django_assistant_bot.bot.keyboards.proxy import (
    PROXY_CLEAR_CALLBACK,
    PROXY_DISABLE_CALLBACK,
    PROXY_ENABLE_CALLBACK,
    PROXY_SET_URL_CALLBACK,
    proxy_keyboard,
)


def get_callbacks(
    *,
    proxy_enabled: bool,
    has_proxy_url: bool,
) -> list[str | None]:
    keyboard = proxy_keyboard(
        proxy_enabled=proxy_enabled,
        has_proxy_url=has_proxy_url,
    )

    return [button.callback_data for row in keyboard.inline_keyboard for button in row]


def test_proxy_without_url_only_shows_set_action() -> None:
    callbacks = get_callbacks(
        proxy_enabled=False,
        has_proxy_url=False,
    )

    assert PROXY_SET_URL_CALLBACK in callbacks

    assert PROXY_ENABLE_CALLBACK not in callbacks

    assert PROXY_DISABLE_CALLBACK not in callbacks

    assert PROXY_CLEAR_CALLBACK not in callbacks


def test_disabled_proxy_with_url_can_be_enabled() -> None:
    callbacks = get_callbacks(
        proxy_enabled=False,
        has_proxy_url=True,
    )

    assert PROXY_ENABLE_CALLBACK in callbacks

    assert PROXY_SET_URL_CALLBACK in callbacks

    assert PROXY_CLEAR_CALLBACK in callbacks


def test_enabled_proxy_can_be_disabled() -> None:
    callbacks = get_callbacks(
        proxy_enabled=True,
        has_proxy_url=True,
    )

    assert PROXY_DISABLE_CALLBACK in callbacks

    assert PROXY_ENABLE_CALLBACK not in callbacks
