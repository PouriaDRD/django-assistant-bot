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
    AppSettingsUpdateSchema,
)
from django_assistant_bot.services.settings import (
    AppSettingsService,
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
# PROXY SETTINGS
# =========================================================


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

    assert updated.proxy_url == "socks5://127.0.0.1:1080"


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


def test_invalid_compression_level_fails() -> None:
    with pytest.raises(
        ValidationError,
    ):
        AppSettingsUpdateSchema(
            compression_level=15,
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
