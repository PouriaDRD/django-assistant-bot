from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

from services.backup.exceptions import MediaBackupError
from services.backup.models import MediaBackupResult


class MediaCollector:
    """
    Scans media files without loading file
    contents into memory.
    """

    def collect(
        self,
        source_path: Path,
    ) -> MediaBackupResult:
        self._validate_source(
            source_path,
        )

        file_count = 0
        total_size = 0

        try:
            for file_path in self.iter_files(
                source_path,
            ):
                try:
                    total_size += file_path.stat().st_size
                except OSError as exc:
                    raise MediaBackupError(
                        "Failed to inspect media file: " f"{file_path}"
                    ) from exc

                file_count += 1

        except OSError as exc:
            raise MediaBackupError(
                "Failed to scan media directory: " f"{source_path}"
            ) from exc

        return MediaBackupResult(
            source_path=source_path,
            file_count=file_count,
            total_size_bytes=total_size,
        )

    @staticmethod
    def iter_files(
        source_path: Path,
    ) -> Iterator[Path]:
        for path in source_path.rglob("*"):
            if path.is_file():
                yield path

    @staticmethod
    def _validate_source(
        source_path: Path,
    ) -> None:
        if not source_path.exists():
            raise MediaBackupError("Media directory does not exist: " f"{source_path}")

        if not source_path.is_dir():
            raise MediaBackupError("Media path is not a directory: " f"{source_path}")
