from __future__ import annotations

from pathlib import Path

from config.settings_manager import SettingsManager
from services.backup import BackupService
from utils.formatters import format_size


def main() -> None:
    settings_manager = SettingsManager(
        config_path=Path("config.json"),
    )

    config = settings_manager.load()

    project = next(
        (project for project in config.projects if project.name == "test"),
        None,
    )

    if project is None:
        raise RuntimeError("Project 'test' was not found.")

    backup_service = BackupService(
        backup_directory=(config.backup.directory),
        compression_level=(config.backup.compression.level),
        retention_enabled=(config.backup.retention.enabled),
        keep_last=(config.backup.retention.keep_last),
    )

    print()
    print("=" * 60)
    print("Starting backup...")
    print("=" * 60)

    result = backup_service.backup_project(
        project,
    )

    print()
    print("=" * 60)
    print("BACKUP SUCCESS")
    print("=" * 60)

    print(f"Project       : {result.project_name}")
    print(f"Status        : {result.status}")

    print("Database size : " f"{format_size(result.database_size_bytes)}")

    print("Media size    : " f"{format_size(result.media_size_bytes)}")

    print("Media files   : " f"{result.media_file_count:,}")

    print("Archive size  : " f"{format_size(result.archive_size_bytes)}")

    print("Archive       : " f"{result.archive_path}")

    print("SHA-256       : " f"{result.checksum.value}")

    print("Duration      : " f"{result.duration_text}")

    print("=" * 60)


if __name__ == "__main__":
    main()
