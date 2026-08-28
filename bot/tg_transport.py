from __future__ import annotations

from urllib.parse import urlparse

from config.models import ProxyConfig


def normalize_proxy_url(
    proxy: ProxyConfig,
) -> str | None:
    if not proxy.enabled:
        return None

    url = proxy.url.strip()

    if not url:
        raise ValueError("Telegram proxy is enabled but proxy URL is empty.")

    parsed = urlparse(url)

    if parsed.scheme not in {
        "http",
        "https",
        "socks4",
        "socks5",
    }:
        raise ValueError("Unsupported Telegram proxy scheme.")

    if parsed.hostname is None:
        raise ValueError("Telegram proxy URL must contain a hostname.")

    return url
