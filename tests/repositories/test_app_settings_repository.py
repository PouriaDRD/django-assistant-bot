from __future__ import annotations

from pathlib import Path

from django_assistant_bot.database.models.enums import (
    CompressionFormat,
)
from django_assistant_bot.database.session import SessionManager
from django_assistant_bot.repositories.app_settings import (
    AppSettingsRepository,
)
from django_assistant_bot.schemas.app_settings import (
    AppSettingsUpdateSchema,
)


def test_settings_are_created_automatically(
    session_manager: SessionManager,
) -> None:
    repository = AppSettingsRepository(
        session_manager,
    )

    settings = repository.get()

    assert settings.bot_enabled is True
    assert settings.backup_enabled is True

    assert settings.backup_directory == Path("./backups")

    assert settings.compression_format is CompressionFormat.ZIP

    assert settings.compression_level == 6

    assert settings.retention_enabled is True
    assert settings.retention_keep_last == 10

    assert settings.proxy_enabled is False
    assert settings.proxy_url == ""


def test_settings_singleton_is_reused(
    session_manager: SessionManager,
) -> None:
    repository = AppSettingsRepository(
        session_manager,
    )

    first = repository.get()
    second = repository.get()

    assert first == second


def test_update_settings(
    session_manager: SessionManager,
) -> None:
    repository = AppSettingsRepository(
        session_manager,
    )

    updated = repository.update(
        AppSettingsUpdateSchema(
            backup_enabled=False,
            compression_level=9,
            retention_keep_last=25,
            proxy_enabled=True,
            proxy_url="socks5://127.0.0.1:1080",
        )
    )

    assert updated.backup_enabled is False
    assert updated.compression_level == 9
    assert updated.retention_keep_last == 25

    assert updated.proxy_enabled is True

    assert updated.proxy_url == "socks5://127.0.0.1:1080"


def test_partial_update_preserves_other_values(
    session_manager: SessionManager,
) -> None:
    repository = AppSettingsRepository(
        session_manager,
    )

    original = repository.get()

    updated = repository.update(
        AppSettingsUpdateSchema(
            compression_level=3,
        )
    )

    assert updated.compression_level == 3

    assert updated.retention_keep_last == original.retention_keep_last

    assert updated.backup_enabled == original.backup_enabled
