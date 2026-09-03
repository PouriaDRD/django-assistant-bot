from __future__ import annotations

import zipfile
from pathlib import Path

from django_assistant_bot.services.backup.exceptions import ArchiveError
from django_assistant_bot.services.backup.media import MediaCollector
from django_assistant_bot.services.backup.models import (
    ArchiveResult,
    DatabaseBackupResult,
    MediaBackupResult,
)


class ArchiveService:
    """
    Creates ZIP archives from database and media
    backup sources.
    """

    def __init__(
        self,
        compression_level: int = 6,
    ) -> None:
        if not 0 <= compression_level <= 9:
            raise ValueError("Compression level must be " "between 0 and 9.")

        self._compression_level = compression_level

    def create(
        self,
        archive_path: Path,
        database: DatabaseBackupResult,
        media: MediaBackupResult | None,
    ) -> ArchiveResult:
        """
        Create the final ZIP backup archive.
        """

        archive_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        try:
            with zipfile.ZipFile(
                archive_path,
                mode="w",
                compression=zipfile.ZIP_DEFLATED,
                compresslevel=self._compression_level,
            ) as archive:
                archive.write(
                    database.backup_path,
                    arcname=(Path("database") / database.backup_path.name),
                )

                if media is not None:
                    self._add_media(
                        archive=archive,
                        media=media,
                    )

        except (
            OSError,
            zipfile.BadZipFile,
        ) as exc:
            raise ArchiveError("Failed to create archive: " f"{archive_path}") from exc

        if not archive_path.exists():
            raise ArchiveError("Archive was not created: " f"{archive_path}")

        return ArchiveResult(
            archive_path=archive_path,
            size_bytes=(archive_path.stat().st_size),
        )

    @staticmethod
    def _add_media(
        *,
        archive: zipfile.ZipFile,
        media: MediaBackupResult,
    ) -> None:
        """
        Add media files to the archive.
        """

        collector = MediaCollector()

        for file_path in collector.iter_files(
            media.source_path,
        ):
            relative_path = file_path.relative_to(
                media.source_path,
            )

            archive.write(
                file_path,
                arcname=(Path("media") / relative_path),
            )
