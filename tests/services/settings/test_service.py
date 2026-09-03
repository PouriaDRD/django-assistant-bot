from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from django_assistant_bot.database.session import SessionManager
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


def test_get_default_settings(
    service: AppSettingsService,
) -> None:
    settings = service.get_settings()

    assert settings.bot_enabled is True
    assert settings.backup_enabled is True
    assert settings.compression_level == 6
    assert settings.retention_keep_last == 10


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
