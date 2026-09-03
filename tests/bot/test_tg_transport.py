from __future__ import annotations

import pytest

from django_assistant_bot.bot.tg_transport import (
    normalize_proxy_url,
)


def test_disabled_proxy_returns_none() -> None:
    result = normalize_proxy_url(
        enabled=False,
        url="",
    )

    assert result is None


def test_valid_http_proxy() -> None:
    result = normalize_proxy_url(
        enabled=True,
        url="http://127.0.0.1:8080",
    )

    assert result == "http://127.0.0.1:8080"


def test_valid_socks5_proxy() -> None:
    result = normalize_proxy_url(
        enabled=True,
        url="socks5://127.0.0.1:1080",
    )

    assert result == "socks5://127.0.0.1:1080"


def test_proxy_url_is_trimmed() -> None:
    result = normalize_proxy_url(
        enabled=True,
        url=("  socks5://127.0.0.1:1080  "),
    )

    assert result == "socks5://127.0.0.1:1080"


def test_enabled_proxy_requires_url() -> None:
    with pytest.raises(
        ValueError,
        match="proxy URL is empty",
    ):
        normalize_proxy_url(
            enabled=True,
            url="   ",
        )


@pytest.mark.parametrize(
    "url",
    [
        "ftp://127.0.0.1:21",
        "ssh://127.0.0.1:22",
        "invalid://127.0.0.1",
    ],
)
def test_unsupported_proxy_scheme_fails(
    url: str,
) -> None:
    with pytest.raises(
        ValueError,
        match="Unsupported",
    ):
        normalize_proxy_url(
            enabled=True,
            url=url,
        )


def test_proxy_requires_hostname() -> None:
    with pytest.raises(
        ValueError,
        match="hostname",
    ):
        normalize_proxy_url(
            enabled=True,
            url="http:///missing-host",
        )
