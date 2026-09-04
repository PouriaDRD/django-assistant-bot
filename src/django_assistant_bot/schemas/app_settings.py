from __future__ import annotations

from pathlib import Path
from urllib.parse import (
    urlsplit,
)

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)

from django_assistant_bot.database.models.enums import (
    CompressionFormat,
)

SUPPORTED_PROXY_SCHEMES = frozenset(
    {
        "http",
        "socks4",
        "socks5",
    }
)


def normalize_proxy_url(
    value: str,
) -> str:
    """
    Normalize and validate a proxy URL.

    Supported schemes:
    - http
    - socks4
    - socks5

    Empty values are allowed so a proxy can remain
    unconfigured while proxy usage is disabled.
    """

    value = value.strip()

    if not value:
        return ""

    try:
        parsed = urlsplit(
            value,
        )

    except ValueError as exc:
        raise ValueError("Proxy URL has an invalid format.") from exc

    scheme = parsed.scheme.lower()

    if scheme not in SUPPORTED_PROXY_SCHEMES:
        raise ValueError(("Proxy scheme must be one of: " "http, socks4, socks5."))

    if not parsed.hostname:
        raise ValueError("Proxy host is required.")

    try:
        port = parsed.port

    except ValueError as exc:
        raise ValueError("Proxy port is invalid.") from exc

    if port is None:
        raise ValueError("Proxy port is required.")

    if not 1 <= port <= 65535:
        raise ValueError(("Proxy port must be between " "1 and 65535."))

    if parsed.query:
        raise ValueError("Proxy URL cannot contain a query string.")

    if parsed.fragment:
        raise ValueError("Proxy URL cannot contain a fragment.")

    if parsed.path not in (
        "",
        "/",
    ):
        raise ValueError("Proxy URL cannot contain a path.")

    return value


class AppSettingsSchema(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )

    bot_enabled: bool = True

    backup_enabled: bool = True

    backup_directory: Path = Path("data/backups")

    compression_format: CompressionFormat = CompressionFormat.ZIP

    compression_level: int = Field(
        default=6,
        ge=0,
        le=9,
    )

    retention_enabled: bool = True

    retention_keep_last: int = Field(
        default=10,
        ge=1,
    )

    proxy_enabled: bool = False

    proxy_url: str = ""

    @field_validator(
        "backup_directory",
    )
    @classmethod
    def normalize_backup_directory(
        cls,
        value: Path,
    ) -> Path:
        """
        Normalize configured backup directory.
        """

        return value.expanduser()

    @field_validator(
        "proxy_url",
    )
    @classmethod
    def validate_proxy_url(
        cls,
        value: str,
    ) -> str:
        """
        Normalize and validate configured proxy URL.
        """

        return normalize_proxy_url(
            value,
        )


class AppSettingsUpdateSchema(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )

    bot_enabled: bool | None = None

    backup_enabled: bool | None = None

    backup_directory: Path | None = None

    compression_format: CompressionFormat | None = None

    compression_level: int | None = Field(
        default=None,
        ge=0,
        le=9,
    )

    retention_enabled: bool | None = None

    retention_keep_last: int | None = Field(
        default=None,
        ge=1,
    )

    proxy_enabled: bool | None = None

    proxy_url: str | None = None

    @field_validator(
        "proxy_url",
    )
    @classmethod
    def validate_proxy_url(
        cls,
        value: str | None,
    ) -> str | None:
        """
        Normalize and validate updated proxy URL.
        """

        if value is None:
            return None

        return normalize_proxy_url(
            value,
        )


__all__ = [
    "AppSettingsSchema",
    "AppSettingsUpdateSchema",
    "SUPPORTED_PROXY_SCHEMES",
    "normalize_proxy_url",
]
