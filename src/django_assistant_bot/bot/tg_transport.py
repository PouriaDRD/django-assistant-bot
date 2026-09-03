from __future__ import annotations

from urllib.parse import urlparse

SUPPORTED_PROXY_SCHEMES = frozenset(
    {
        "http",
        "https",
        "socks4",
        "socks5",
    }
)


def normalize_proxy_url(
    *,
    enabled: bool,
    url: str,
) -> str | None:
    """
    Normalize and validate Telegram proxy configuration.

    Returns None when proxy support is disabled.
    """

    if not enabled:
        return None

    normalized_url = url.strip()

    if not normalized_url:
        raise ValueError("Telegram proxy is enabled but proxy URL is empty.")

    parsed = urlparse(
        normalized_url,
    )

    if parsed.scheme not in SUPPORTED_PROXY_SCHEMES:
        raise ValueError("Unsupported Telegram proxy scheme.")

    if parsed.hostname is None:
        raise ValueError("Telegram proxy URL must contain a hostname.")

    return normalized_url
