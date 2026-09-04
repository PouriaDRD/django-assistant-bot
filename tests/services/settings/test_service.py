from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from django_assistant_bot.database.session import (
    SessionManager,
)
from django_assistant_bot.repositories.app_settings import (
    AppSettingsRepository,
)
from django_assistant_bot.schemas.app_settings import (
    AppSettingsSchema,
    AppSettingsUpdateSchema,
)
from django_assistant_bot.services.settings import (
    AppSettingsService,
    ProxyConfigurationError,
)


@pytest.fixture()
def service(
    session_manager: SessionManager,
) -> AppSettingsService:
    return AppSettingsService(
        AppSettingsRepository(
            session_manager,
        )
    )


# =========================================================
# DEFAULTS
# =========================================================


def test_get_default_settings(
    service: AppSettingsService,
) -> None:
    settings = service.get_settings()

    assert settings.bot_enabled is True
    assert settings.backup_enabled is True
    assert settings.compression_level == 6
    assert settings.retention_keep_last == 10
    assert settings.proxy_enabled is False
    assert settings.proxy_url == ""


# =========================================================
# BOT STATE
# =========================================================


def test_disable_bot(
    service: AppSettingsService,
) -> None:
    updated = service.disable_bot()

    assert updated.bot_enabled is False

    persisted = service.get_settings()

    assert persisted.bot_enabled is False


def test_enable_bot(
    service: AppSettingsService,
) -> None:
    service.disable_bot()

    updated = service.enable_bot()

    assert updated.bot_enabled is True

    persisted = service.get_settings()

    assert persisted.bot_enabled is True


def test_is_bot_enabled(
    service: AppSettingsService,
) -> None:
    assert service.is_bot_enabled() is True

    service.disable_bot()

    assert service.is_bot_enabled() is False

    service.enable_bot()

    assert service.is_bot_enabled() is True


# =========================================================
# BACKUP SETTINGS
# =========================================================


def test_update_backup_settings(
    service: AppSettingsService,
) -> None:
    updated = service.update_settings(
        AppSettingsUpdateSchema(
            backup_enabled=False,
            backup_directory=Path("custom-backups"),
            compression_level=9,
            retention_keep_last=20,
        )
    )

    assert updated.backup_enabled is False

    assert updated.backup_directory == Path("custom-backups")

    assert updated.compression_level == 9

    assert updated.retention_keep_last == 20


# =========================================================
# COMPRESSION SETTINGS
# =========================================================


def test_set_compression_level(
    service: AppSettingsService,
) -> None:
    updated = service.set_compression_level(
        8,
    )

    assert updated.compression_level == 8

    persisted = service.get_settings()

    assert persisted.compression_level == 8


def test_set_minimum_compression_level(
    service: AppSettingsService,
) -> None:
    updated = service.set_compression_level(
        0,
    )

    assert updated.compression_level == 0

    persisted = service.get_settings()

    assert persisted.compression_level == 0


def test_set_maximum_compression_level(
    service: AppSettingsService,
) -> None:
    updated = service.set_compression_level(
        9,
    )

    assert updated.compression_level == 9

    persisted = service.get_settings()

    assert persisted.compression_level == 9


def test_compression_helper_preserves_other_settings(
    service: AppSettingsService,
) -> None:
    service.disable_bot()
    service.disable_backups()

    service.set_retention_keep_last(
        25,
    )

    updated = service.set_compression_level(
        3,
    )

    assert updated.compression_level == 3
    assert updated.bot_enabled is False
    assert updated.backup_enabled is False
    assert updated.retention_keep_last == 25


# =========================================================
# PROXY SETTINGS
# =========================================================


@pytest.mark.parametrize(
    "proxy_url",
    [
        "http://127.0.0.1:8080",
        "http://proxy.example.com:3128",
        "socks4://127.0.0.1:1080",
        "socks5://127.0.0.1:1080",
        "socks5://proxy.example.com:1080",
        "socks5://user:password@127.0.0.1:1080",
        "socks5://user:password@proxy.example.com:1080",
    ],
)
def test_supported_proxy_urls_are_valid(
    proxy_url: str,
) -> None:
    settings = AppSettingsUpdateSchema(
        proxy_url=proxy_url,
    )

    assert settings.proxy_url == proxy_url


def test_proxy_url_is_trimmed() -> None:
    settings = AppSettingsUpdateSchema(
        proxy_url=("  socks5://127.0.0.1:1080  "),
    )

    assert settings.proxy_url == ("socks5://127.0.0.1:1080")


def test_empty_proxy_url_is_valid() -> None:
    settings = AppSettingsUpdateSchema(
        proxy_url="",
    )

    assert settings.proxy_url == ""


@pytest.mark.parametrize(
    "proxy_url",
    [
        "https://127.0.0.1:8080",
        "ftp://127.0.0.1:21",
        "mtproto://127.0.0.1:443",
        "ssh://127.0.0.1:22",
    ],
)
def test_unsupported_proxy_scheme_fails(
    proxy_url: str,
) -> None:
    with pytest.raises(
        ValidationError,
    ):
        AppSettingsUpdateSchema(
            proxy_url=proxy_url,
        )


@pytest.mark.parametrize(
    "proxy_url",
    [
        "socks5://",
        "socks5://:1080",
        "http://:8080",
    ],
)
def test_proxy_without_host_fails(
    proxy_url: str,
) -> None:
    with pytest.raises(
        ValidationError,
    ):
        AppSettingsUpdateSchema(
            proxy_url=proxy_url,
        )


@pytest.mark.parametrize(
    "proxy_url",
    [
        "socks5://127.0.0.1",
        "http://proxy.example.com",
        "socks4://localhost",
    ],
)
def test_proxy_without_port_fails(
    proxy_url: str,
) -> None:
    with pytest.raises(
        ValidationError,
    ):
        AppSettingsUpdateSchema(
            proxy_url=proxy_url,
        )


@pytest.mark.parametrize(
    "proxy_url",
    [
        "socks5://127.0.0.1:0",
        "socks5://127.0.0.1:65536",
        "socks5://127.0.0.1:not-a-port",
    ],
)
def test_invalid_proxy_port_fails(
    proxy_url: str,
) -> None:
    with pytest.raises(
        ValidationError,
    ):
        AppSettingsUpdateSchema(
            proxy_url=proxy_url,
        )


@pytest.mark.parametrize(
    "proxy_url",
    [
        "socks5://127.0.0.1:1080/path",
        "socks5://127.0.0.1:1080?foo=bar",
        "socks5://127.0.0.1:1080#fragment",
    ],
)
def test_proxy_with_unsupported_url_components_fails(
    proxy_url: str,
) -> None:
    with pytest.raises(
        ValidationError,
    ):
        AppSettingsUpdateSchema(
            proxy_url=proxy_url,
        )


def test_update_proxy_settings(
    service: AppSettingsService,
) -> None:
    updated = service.update_settings(
        AppSettingsUpdateSchema(
            proxy_enabled=True,
            proxy_url=("socks5://127.0.0.1:1080"),
        )
    )

    assert updated.proxy_enabled is True

    assert updated.proxy_url == ("socks5://127.0.0.1:1080")


def test_set_proxy_url(
    service: AppSettingsService,
) -> None:
    updated = service.set_proxy_url(
        "socks5://127.0.0.1:1080",
    )

    assert updated.proxy_enabled is False

    assert updated.proxy_url == ("socks5://127.0.0.1:1080")

    persisted = service.get_settings()

    assert persisted.proxy_enabled is False

    assert persisted.proxy_url == ("socks5://127.0.0.1:1080")


def test_set_proxy_url_does_not_enable_proxy(
    service: AppSettingsService,
) -> None:
    updated = service.set_proxy_url(
        "http://127.0.0.1:8080",
    )

    assert updated.proxy_enabled is False


def test_enable_proxy(
    service: AppSettingsService,
) -> None:
    service.set_proxy_url(
        "socks5://127.0.0.1:1080",
    )

    updated = service.enable_proxy()

    assert updated.proxy_enabled is True

    assert updated.proxy_url == ("socks5://127.0.0.1:1080")

    persisted = service.get_settings()

    assert persisted.proxy_enabled is True


def test_enable_proxy_without_url_fails(
    service: AppSettingsService,
) -> None:
    with pytest.raises(
        ProxyConfigurationError,
    ):
        service.enable_proxy()

    persisted = service.get_settings()

    assert persisted.proxy_enabled is False
    assert persisted.proxy_url == ""


def test_disable_proxy_preserves_url(
    service: AppSettingsService,
) -> None:
    service.set_proxy_url(
        "socks5://127.0.0.1:1080",
    )

    service.enable_proxy()

    updated = service.disable_proxy()

    assert updated.proxy_enabled is False

    assert updated.proxy_url == ("socks5://127.0.0.1:1080")


def test_clear_proxy_disables_and_removes_url(
    service: AppSettingsService,
) -> None:
    service.set_proxy_url(
        "socks5://127.0.0.1:1080",
    )

    service.enable_proxy()

    updated = service.clear_proxy()

    assert updated.proxy_enabled is False
    assert updated.proxy_url == ""

    persisted = service.get_settings()

    assert persisted.proxy_enabled is False
    assert persisted.proxy_url == ""


def test_proxy_helpers_preserve_other_settings(
    service: AppSettingsService,
) -> None:
    service.disable_bot()
    service.disable_backups()
    service.disable_retention()

    service.set_compression_level(
        3,
    )

    service.set_retention_keep_last(
        25,
    )

    service.set_proxy_url(
        "socks5://127.0.0.1:1080",
    )

    updated = service.enable_proxy()

    assert updated.proxy_enabled is True
    assert updated.bot_enabled is False
    assert updated.backup_enabled is False
    assert updated.retention_enabled is False
    assert updated.compression_level == 3
    assert updated.retention_keep_last == 25


def test_schema_rejects_invalid_persisted_proxy_url() -> None:
    with pytest.raises(
        ValidationError,
    ):
        AppSettingsSchema(
            proxy_enabled=False,
            proxy_url="invalid-proxy",
        )


# =========================================================
# PARTIAL UPDATE
# =========================================================


def test_partial_update_keeps_existing_values(
    service: AppSettingsService,
) -> None:
    before = service.get_settings()

    after = service.update_settings(
        AppSettingsUpdateSchema(
            compression_level=3,
        )
    )

    assert after.compression_level == 3

    assert after.retention_keep_last == before.retention_keep_last

    assert after.backup_enabled == before.backup_enabled

    assert after.bot_enabled == before.bot_enabled


# =========================================================
# VALIDATION
# =========================================================


def test_invalid_compression_level_above_max_fails() -> None:
    with pytest.raises(
        ValidationError,
    ):
        AppSettingsUpdateSchema(
            compression_level=10,
        )


def test_invalid_compression_level_below_min_fails() -> None:
    with pytest.raises(
        ValidationError,
    ):
        AppSettingsUpdateSchema(
            compression_level=-1,
        )


def test_invalid_retention_value_fails() -> None:
    with pytest.raises(
        ValidationError,
    ):
        AppSettingsUpdateSchema(
            retention_keep_last=0,
        )


def test_disable_and_enable_backups(
    service: AppSettingsService,
) -> None:
    disabled = service.disable_backups()

    assert disabled.backup_enabled is False

    enabled = service.enable_backups()

    assert enabled.backup_enabled is True


def test_backup_state_helpers_preserve_bot_state(
    service: AppSettingsService,
) -> None:
    service.disable_bot()

    settings = service.disable_backups()

    assert settings.bot_enabled is False
    assert settings.backup_enabled is False


# =========================================================
# RETENTION SETTINGS
# =========================================================


def test_disable_retention(
    service: AppSettingsService,
) -> None:
    updated = service.disable_retention()

    assert updated.retention_enabled is False

    persisted = service.get_settings()

    assert persisted.retention_enabled is False


def test_enable_retention(
    service: AppSettingsService,
) -> None:
    service.disable_retention()

    updated = service.enable_retention()

    assert updated.retention_enabled is True

    persisted = service.get_settings()

    assert persisted.retention_enabled is True


def test_set_retention_keep_last(
    service: AppSettingsService,
) -> None:
    updated = service.set_retention_keep_last(
        25,
    )

    assert updated.retention_keep_last == 25

    persisted = service.get_settings()

    assert persisted.retention_keep_last == 25


def test_retention_helpers_preserve_other_settings(
    service: AppSettingsService,
) -> None:
    service.disable_bot()
    service.disable_backups()

    updated = service.set_retention_keep_last(
        15,
    )

    assert updated.retention_keep_last == 15
    assert updated.bot_enabled is False
    assert updated.backup_enabled is False


def test_invalid_retention_keep_last_fails() -> None:
    with pytest.raises(
        ValidationError,
    ):
        AppSettingsUpdateSchema(
            retention_keep_last=0,
        )


def test_changing_proxy_url_disables_enabled_proxy(
    service: AppSettingsService,
) -> None:
    service.set_proxy_url(
        "socks5://127.0.0.1:1080",
    )

    service.enable_proxy()

    before = service.get_settings()

    assert before.proxy_enabled is True

    updated = service.set_proxy_url(
        "socks5://127.0.0.1:1081",
    )

    assert updated.proxy_enabled is False

    assert updated.proxy_url == ("socks5://127.0.0.1:1081")

    persisted = service.get_settings()

    assert persisted.proxy_enabled is False

    assert persisted.proxy_url == ("socks5://127.0.0.1:1081")
